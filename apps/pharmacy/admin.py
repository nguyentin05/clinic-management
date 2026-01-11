from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, F
from apps.pharmacy.models import Medicine, MedicineCategory, Prescription, PrescriptionDetail, DispenseLog, \
    ImportReceipt, ImportDetail, DailyInventorySnapshot

from clinic_management.admin import admin_site


class PrescriptionDetailInline(admin.TabularInline):
    model = PrescriptionDetail
    extra = 1
    fields = ['medicine', 'quantity', 'dosage']
    autocomplete_fields = ['medicine']


class ImportDetailInline(admin.TabularInline):
    model = ImportDetail
    extra = 1
    fields = ['medicine', 'quantity', 'cost']
    autocomplete_fields = ['medicine']


class MedicineCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'medicine_count', 'active', 'created_date']
    search_fields = ['name']

    def medicine_count(self, obj):
        count = obj.medicine_set.filter(active=True).count()
        return format_html('<span style="color: green; font-weight: bold;">{}</span>', count)

    medicine_count.short_description = 'Số thuốc'


class MedicineAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'unit', 'price_display',
        'stock_display', 'cost_display', 'active'
    ]
    list_filter = ['category', 'unit', 'active', 'created_date']
    search_fields = ['name', 'description']
    list_editable = ['active']

    fieldsets = (
        ('Thông tin thuốc', {
            'fields': ('name', 'category', 'unit', 'description', 'image')
        }),
        ('Giá & Tồn kho', {
            'fields': (('price', 'cost'), 'current_stock')
        }),
        ('Trạng thái', {
            'fields': ('active',)
        }),
    )

    def price_display(self, obj):
        return format_html(
            '<span style="color: green; font-weight: bold;">{} VNĐ</span>',
            obj.price
        )

    price_display.short_description = 'Giá bán'

    def cost_display(self, obj):
        return format_html(
            '<span style="color: blue;">{} VNĐ</span>',
            obj.cost
        )

    cost_display.short_description = 'Giá nhập'

    def stock_display(self, obj):
        if obj.current_stock < 10:
            color = 'red'
            icon = '⚠️'
        elif obj.current_stock < 50:
            color = 'orange'
            icon = '⚡'
        else:
            color = 'green'
            icon = '✓'

        return format_html(
            '{} <span style="color: {}; font-weight: bold;">{}</span>',
            icon, color, obj.current_stock
        )

    stock_display.short_description = 'Tồn kho'

    actions = ['export_low_stock']

    def export_low_stock(self, request, queryset):
        low_stock = queryset.filter(current_stock__lt=10)
        self.message_user(request, f'Có {low_stock.count()} thuốc sắp hết')

    export_low_stock.short_description = 'Xuất danh sách thuốc sắp hết'


class PrescriptionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'appointment_link', 'doctor_name', 'patient_name',
        'item_count', 'created_date'
    ]
    search_fields = [
        'appointment__doctor__email',
        'appointment__patient__email',
        'note'
    ]
    date_hierarchy = 'created_date'
    inlines = [PrescriptionDetailInline]

    fieldsets = (
        ('Lịch hẹn', {
            'fields': ('appointment',)
        }),
        ('Ghi chú', {
            'fields': ('note',)
        }),
    )

    readonly_fields = ['appointment']

    def appointment_link(self, obj):
        url = reverse('admin:clinic_appointment_change', args=[obj.appointment.id])
        date = obj.appointment.date.strftime('%d/%m/%Y')
        return format_html('<a href="{}">Lịch hẹn {}</a>', url, date)

    appointment_link.short_description = 'Lịch hẹn'

    def doctor_name(self, obj):
        return obj.appointment.doctor.get_full_name()

    doctor_name.short_description = 'Bác sĩ'

    def patient_name(self, obj):
        return obj.appointment.patient.get_full_name()

    patient_name.short_description = 'Bệnh nhân'

    def item_count(self, obj):
        count = obj.items.count()
        return format_html('<span style="color: blue; font-weight: bold;">{} thuốc</span>', count)

    item_count.short_description = 'Số loại thuốc'


class PrescriptionDetailAdmin(admin.ModelAdmin):
    list_display = [
        'prescription_link', 'medicine', 'quantity',
        'dosage', 'created_date'
    ]
    list_filter = ['medicine', 'created_date']
    search_fields = ['medicine__name', 'dosage']

    def prescription_link(self, obj):
        url = reverse('admin:pharmacy_prescription_change', args=[obj.prescription.id])
        return format_html('<a href="{}">Đơn thuốc #{}</a>', url, obj.prescription.id)

    prescription_link.short_description = 'Đơn thuốc'


class DispenseLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'pharmacist_name', 'prescription_link',
        'medicine', 'quantity', 'created_date'
    ]
    list_filter = ['pharmacist', 'created_date']
    search_fields = ['medicine__name', 'prescription__id']
    date_hierarchy = 'created_date'

    def pharmacist_name(self, obj):
        return obj.pharmacist.get_full_name() if obj.pharmacist else '-'

    pharmacist_name.short_description = 'Dược sĩ'

    def prescription_link(self, obj):
        url = reverse('admin:pharmacy_prescription_change', args=[obj.prescription.id])
        return format_html('<a href="{}">#{}</a>', url, obj.prescription.id)

    prescription_link.short_description = 'Đơn thuốc'


class ImportReceiptAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'pharmacist_name', 'status_display',
        'total_items', 'total_cost', 'created_date'
    ]
    list_filter = ['status', 'pharmacist', 'created_date']
    search_fields = ['note']
    date_hierarchy = 'created_date'
    inlines = [ImportDetailInline]

    fieldsets = (
        ('Thông tin phiếu nhập', {
            'fields': ('pharmacist', 'status', 'note')
        }),
    )

    actions = ['mark_completed', 'mark_cancelled']

    def pharmacist_name(self, obj):
        return obj.pharmacist.get_full_name() if obj.pharmacist else '-'

    pharmacist_name.short_description = 'Dược sĩ'

    def status_display(self, obj):
        colors = {
            'DRAFT': 'gray',
            'COMPLETED': 'green',
            'CANCELED': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )

    status_display.short_description = 'Trạng thái'

    def total_items(self, obj):
        count = obj.details.count()
        return f"{count} loại thuốc"

    total_items.short_description = 'Số mặt hàng'

    def total_cost(self, obj):
        total = obj.details.aggregate(
            total=Sum(F('quantity') * F('cost'))
        )['total'] or 0
        return format_html(
            '<span style="color: blue; font-weight: bold;">{} VNĐ</span>',
            total
        )

    total_cost.short_description = 'Tổng giá trị'

    def mark_completed(self, request, queryset):
        updated = 0
        for receipt in queryset.filter(status='DRAFT'):
            # Update stock
            for detail in receipt.details.all():
                detail.medicine.current_stock += detail.quantity
                detail.medicine.save()
            receipt.status = 'COMPLETED'
            receipt.save()
            updated += 1

        self.message_user(request, f'Đã hoàn thành {updated} phiếu nhập kho')

    mark_completed.short_description = 'Hoàn thành nhập kho'

    def mark_cancelled(self, request, queryset):
        updated = queryset.filter(status='DRAFT').update(status='CANCELED')
        self.message_user(request, f'Đã hủy {updated} phiếu nhập')

    mark_cancelled.short_description = 'Hủy phiếu nhập'


class ImportDetailAdmin(admin.ModelAdmin):
    list_display = ['receipt_link', 'medicine', 'quantity', 'cost', 'total_cost']
    list_filter = ['receipt__status', 'medicine']
    search_fields = ['medicine__name']

    def receipt_link(self, obj):
        url = reverse('admin:pharmacy_importreceipt_change', args=[obj.receipt.id])
        return format_html('<a href="{}">Phiếu #{}</a>', url, obj.receipt.id)

    receipt_link.short_description = 'Phiếu nhập'

    def total_cost(self, obj):
        total = obj.quantity * obj.cost
        return format_html('{} VNĐ', total)

    total_cost.short_description = 'Thành tiền'


class DailyInventorySnapshotAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'medicine', 'opening_quantity',
        'import_quantity', 'export_quantity', 'closing_quantity'
    ]
    list_filter = ['date', 'medicine']
    search_fields = ['medicine__name']
    date_hierarchy = 'date'

    def has_add_permission(self, request):
        return False  # Auto-generated, không cho add manual

    def has_delete_permission(self, request, obj=None):
        return False  # Không cho xóa historical data


admin_site.register(MedicineCategory, MedicineCategoryAdmin)
admin_site.register(Medicine, MedicineAdmin)
admin_site.register(Prescription, PrescriptionAdmin)
admin_site.register(PrescriptionDetail, PrescriptionDetailAdmin)
admin_site.register(DispenseLog, DispenseLogAdmin)
admin_site.register(ImportReceipt, ImportReceiptAdmin)
admin_site.register(ImportDetail, ImportDetailAdmin)
admin_site.register(DailyInventorySnapshot, DailyInventorySnapshotAdmin)
