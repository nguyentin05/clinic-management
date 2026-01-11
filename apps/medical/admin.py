from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from apps.medical.models import MedicalRecord, TestOrder, TestStatus
from clinic_management.admin import admin_site


class TestOrderInline(admin.TabularInline):
    model = TestOrder
    extra = 0
    fields = ['service', 'status', 'nurse', 'result', 'note']
    readonly_fields = ['service']
    show_change_link = True


class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = [
        'appointment_link', 'doctor_name', 'patient_name',
        'diagnosis_preview'
    ]
    search_fields = [
        'appointment__doctor__email', 'appointment__doctor__first_name',
        'appointment__patient__email', 'appointment__patient__first_name',
        'diagnosis'
    ]
    inlines = [TestOrderInline]

    fieldsets = (
        ('Lịch hẹn', {
            'fields': ('appointment',)
        }),
        ('Triệu chứng & Chẩn đoán', {
            'fields': ('symptoms', 'diagnosis')
        }),
        ('Kế hoạch điều trị', {
            'fields': ('treatment_plan',)
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

    def diagnosis_preview(self, obj):
        if obj.diagnosis:
            preview = obj.diagnosis[:50]
            return f"{preview}..." if len(obj.diagnosis) > 50 else preview
        return '-'

    diagnosis_preview.short_description = 'Chẩn đoán'


class TestOrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'medical_record_link', 'service', 'status_display',
        'nurse_name', 'confirmed_date', 'completed_date'
    ]
    list_filter = ['status', 'service', 'confirmed_date']
    search_fields = [
        'medical_record__appointment__patient__email',
        'medical_record__appointment__patient__first_name',
        'service__name'
    ]
    date_hierarchy = 'created_date'

    fieldsets = (
        ('Thông tin xét nghiệm', {
            'fields': ('medical_record', 'service')
        }),
        ('Trạng thái', {
            'fields': ('status', 'nurse')
        }),
        ('Kết quả', {
            'fields': ('result', 'note')
        }),
        ('Thời gian', {
            'fields': ('confirmed_date', 'completed_date'),
            'classes': ('collapse',)
        }),
        ('Hủy/Xóa', {
            'fields': ('reason', 'deleted_date', 'deleted_by'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['confirmed_date', 'completed_date', 'deleted_date']

    actions = ['mark_processing', 'mark_completed', 'mark_cancelled']

    def medical_record_link(self, obj):
        url = reverse('admin:medical_medicalrecord_change', args=[obj.medical_record.appointment_id])
        patient = obj.medical_record.appointment.patient.get_full_name()
        return format_html('<a href="{}">{}</a>', url, patient)

    medical_record_link.short_description = 'Bệnh án'

    def status_display(self, obj):
        colors = {
            'REQUESTED': 'orange',
            'PROCESSING': 'blue',
            'COMPLETED': 'green',
            'CANCELLED': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )

    status_display.short_description = 'Trạng thái'

    def nurse_name(self, obj):
        return obj.nurse.get_full_name() if obj.nurse else '-'

    nurse_name.short_description = 'Y tá xử lý'

    def mark_processing(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=TestStatus.REQUESTED).update(
            status=TestStatus.PROCESSING,
            confirmed_date=timezone.now(),
            nurse=request.user
        )
        self.message_user(request, f'Đã chuyển {updated} xét nghiệm sang trạng thái Đang xử lý')

    mark_processing.short_description = 'Đánh dấu đang xử lý'

    def mark_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=TestStatus.PROCESSING).update(
            status=TestStatus.COMPLETED,
            completed_date=timezone.now()
        )
        self.message_user(request, f'Đã hoàn thành {updated} xét nghiệm')

    mark_completed.short_description = 'Đánh dấu hoàn thành'

    def mark_cancelled(self, request, queryset):
        from django.utils import timezone
        updated = queryset.exclude(status=TestStatus.CANCELLED).update(
            status=TestStatus.CANCELLED,
            deleted_date=timezone.now(),
            deleted_by=request.user
        )
        self.message_user(request, f'Đã hủy {updated} xét nghiệm')

    mark_cancelled.short_description = 'Hủy xét nghiệm'


admin_site.register(TestOrder, TestOrderAdmin)
admin_site.register(MedicalRecord, MedicalRecordAdmin)
