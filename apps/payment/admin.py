from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum
from django.utils import timezone

from clinic_management.admin import admin_site
from .models import Payment


class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'patient_link', 'amount_display', 'method_display',
        'is_paid_display', 'source_display', 'paid_date', 'created_date'
    ]
    list_filter = ['is_paid', 'method', 'paid_date', 'created_date']
    search_fields = [
        'patient__email', 'patient__first_name',
        'transaction_id'
    ]
    date_hierarchy = 'created_date'

    fieldsets = (
        ('Thông tin thanh toán', {
            'fields': ('patient', 'amount', 'method')
        }),
        ('Nguồn thanh toán', {
            'fields': ('appointment', 'prescription')
        }),
        ('Trạng thái', {
            'fields': ('is_paid', 'paid_date', 'nurse', 'transaction_id')
        }),
    )

    readonly_fields = ['paid_date']

    actions = ['mark_as_paid', 'export_revenue_report']

    def patient_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.get_full_name())

    patient_link.short_description = 'Bệnh nhân'

    def amount_display(self, obj):
        return format_html(
            '<span style="color: green; font-weight: bold;">{} VNĐ</span>',
            obj.amount
        )

    amount_display.short_description = 'Số tiền'

    def method_display(self, obj):
        if obj.method:
            icons = {
                'CASH': '💵',
                'BANKING': '🏦'
            }
            icon = icons.get(obj.method, '💳')
            return format_html('{} {}', icon, obj.get_method_display())
        return '-'

    method_display.short_description = 'Phương thức'

    def is_paid_display(self, obj):
        if obj.is_paid:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Đã thanh toán</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Chưa thanh toán</span>'
        )

    is_paid_display.short_description = 'Trạng thái'

    def source_display(self, obj):
        if obj.appointment:
            url = reverse('admin:clinic_appointment_change', args=[obj.appointment.id])
            return format_html(
                '🏥 <a href="{}">Lịch hẹn #{}</a>',
                url, obj.appointment.id
            )
        elif obj.prescription:
            url = reverse('admin:pharmacy_prescription_change', args=[obj.prescription.id])
            return format_html(
                '💊 <a href="{}">Đơn thuốc #{}</a>',
                url, obj.prescription.id
            )
        return '-'

    source_display.short_description = 'Nguồn'

    def mark_as_paid(self, request, queryset):
        updated = queryset.filter(is_paid=False).update(
            is_paid=True,
            paid_date=timezone.now(),
            nurse=request.user
        )
        self.message_user(request, f'Đã đánh dấu {updated} thanh toán hoàn thành')

    mark_as_paid.short_description = 'Đánh dấu đã thanh toán'

    def export_revenue_report(self, request, queryset):
        total = queryset.filter(is_paid=True).aggregate(total=Sum('amount'))['total'] or 0
        count = queryset.filter(is_paid=True).count()
        self.message_user(
            request,
            f'Tổng doanh thu: {total:,.0f} VNĐ từ {count} giao dịch'
        )

    export_revenue_report.short_description = 'Xem báo cáo doanh thu'


admin_site.register(Payment, PaymentAdmin)
