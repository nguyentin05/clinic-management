from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.clinic.models import AppointmentStatus
from apps.payment.signals import dispense_completed
from apps.pharmacy.models import PrescriptionDetail, Prescription, Medicine, DispenseLog, ImportReceiptStatus, \
    ImportReceipt, ImportDetail


class PrescriptionDetailsSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_unit = serializers.CharField(source='medicine.unit', read_only=True)
    medicine_id = serializers.PrimaryKeyRelatedField(queryset=Medicine.objects.filter(active=True), source='medicine',
                                                     write_only=True)

    class Meta:
        model = PrescriptionDetail
        fields = ['id', 'medicine_id', 'medicine_name', 'medicine_unit', 'quantity', 'dosage']
        read_only_fields = ['id']


class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionDetailsSerializer(many=True)

    class Meta:
        model = Prescription
        fields = ['id', 'created_date', 'note', 'items']
        read_only_fields = ['id', 'created_date']

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Đơn thuốc phải có ít nhất một loại thuốc.")

        return value

    def validate(self, attrs):
        appointment = self.context['appointment']

        if not appointment and self.instance:
            appointment = self.instance.appointment

        if appointment.status != AppointmentStatus.IN_PROCESS:
            raise serializers.ValidationError('Chỉ được kê đơn khi cuộc hẹn đang diễn ra')

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        appointment = self.context['appointment']

        prescription = Prescription.objects.create(appointment=appointment, **validated_data)

        items = [
            PrescriptionDetail(prescription=prescription, **item)
            for item in items_data
        ]
        PrescriptionDetail.objects.bulk_create(items)

        return prescription

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items')

        instance.note = validated_data.get('note', instance.note)
        instance.save()

        instance.items.all().delete()

        items = [
            PrescriptionDetail(prescription=instance, **item)
            for item in items_data
        ]
        PrescriptionDetail.objects.bulk_create(items)

        return instance


class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = ['id', 'name', 'category']


class MedicineDetailSerializer(MedicineSerializer):
    class Meta:
        model = MedicineSerializer.Meta.model
        fields = MedicineSerializer.Meta.fields + ['unit', 'price', 'description', 'image', 'current_stock']


class DispenseSerializer(serializers.Serializer):
    def validate(self, attrs):
        prescription = self.context.get('prescription')

        items = prescription.items.select_related('medicine').all()

        for item in items:
            medicine = item.medicine
            qty = item.quantity

            if medicine.current_stock < qty:
                raise serializers.ValidationError("Không đủ tồn kho để xuất đơn này.")

        attrs['items'] = items
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        prescription = self.context['prescription']
        items = validated_data['items']
        user = self.context['request'].user

        logs = []
        total_amount = 0

        for item in items:
            item.medicine.current_stock -= item.quantity
            item.medicine.save()

            logs.append(DispenseLog(
                pharmacist=user,
                prescription=prescription,
                medicine=item.medicine,
                quantity=item.quantity
            ))

            total_amount += (item.medicine.price * item.quantity)

        DispenseLog.objects.bulk_create(logs)

        dispense_completed.send(
            sender=self.__class__,
            prescription=prescription,
            total_amount=total_amount
        )

        return validated_data


# detail trong 1 phieu nhap
class ImportDetailSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_unit = serializers.CharField(source='medicine.unit', read_only=True)
    medicine_id = serializers.PrimaryKeyRelatedField(queryset=Medicine.objects.filter(active=True), source='medicine',
                                                     write_only=True)

    class Meta:
        model = ImportDetail
        fields = ['id', 'medicine_id', 'medicine_name', 'medicine_unit', 'quantity']
        read_only_fields = ['id']

#xem cơ bản phiếu nhập cho list
class ImportReceiptSerializer(serializers.ModelSerializer):
    pharmacist_name = serializers.CharField(source='pharmacist.get_full_name', read_only=True)
    created_date = serializers.DateTimeField(format="%d/%m/%Y", read_only=True)

    class Meta:
        model = ImportReceipt
        fields = ['id', 'created_date', 'status', 'pharmacist_name']
        read_only_fields = ['id', 'created_date', 'status']


# xem chi tiet phieu nhap
class ImportReceiptDetailSerializer(ImportReceiptSerializer):
    details = ImportDetailSerializer(many=True)

    class Meta:
        model = ImportReceiptSerializer.Meta.model
        fields = ImportReceiptSerializer.Meta.fields + ['note', 'details']
        read_only_fields = ImportReceiptSerializer.Meta.read_only_fields

    def validate_details(self, value):
        if not value:
            raise serializers.ValidationError("Phiếu nhập phải có ít nhất một loại thuốc.")

        return value

    # tao phiếu nhập thuốc của dược sĩ
    @transaction.atomic
    def create(self, validated_data):
        details_data = validated_data.pop('details')
        pharmacist = self.context['request'].user

        receipt = ImportReceipt.objects.create(pharmacist=pharmacist,
                                               status=ImportReceiptStatus.DRAFT,
                                               **validated_data)
        receipt.save()

        for detail in details_data:
            medicine = detail['medicine']

            ImportDetail.objects.create(
                receipt=receipt,
                cost=medicine.cost,
                **detail
            )

        return receipt

    @transaction.atomic
    def update(self, instance, validated_data):
        if instance.status == ImportReceiptStatus.COMPLETED:
            raise serializers.ValidationError("Không thể chỉnh sửa phiếu đã hoàn tất.")

        details_data = validated_data.pop('details')

        instance.note = validated_data.get('note', instance.note)
        instance.save()

        instance.details.all().delete()

        for detail in details_data:
            medicine = detail['medicine']

            ImportDetail.objects.create(
                receipt=instance,
                cost=medicine.cost,
                **detail
            )

        return instance

#commit phiếu nhập hàng
class ChangeReceiptSerializer(serializers.Serializer):
    def validate(self, attrs):
        receipt = self.context['receipt']
        action = self.context['action']

        if receipt.status in [ImportReceiptStatus.CANCELED, ImportReceiptStatus.COMPLETED]:
            raise ValidationError(f"Phiếu nhập này đã '{receipt.get_status_display()}', không thể '{action}'.")


        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        action = self.context['action']
        if action == 'commit':
            for detail in instance.details.select_related('medicine').all():
                medicine = detail.medicine

                medicine.current_stock += detail.quantity

                medicine.save()

            instance.status = ImportReceiptStatus.COMPLETED

        elif action == 'cancel':
            instance.status = ImportReceiptStatus.CANCELED
            instance.active = False


        instance.save()
        return instance