from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from apps.clinic.models import Specialty, Service, WorkSchedule, Room, Appointment, Review
from clinic_management.admin import admin_site


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1
    fields = ['name', 'price', 'duration', 'active']
    show_change_link = True


class WorkScheduleInline(admin.TabularInline):
    model = WorkSchedule
    extra = 1
    fields = ['day_of_week', 'start_time', 'end_time', 'shift', 'is_appointable']
    readonly_fields = ['shift']


class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ['name', 'service_count', 'doctor_count', 'active', 'created_date']
    list_filter = ['active', 'created_date']
    search_fields = ['name', 'description']
    inlines = [ServiceInline]

    def service_count(self, obj):
        count = obj.services.filter(active=True).count()
        return format_html('<span style="color: green; font-weight: bold;">{}</span>', count)

    service_count.short_description = 'Số dịch vụ'

    def doctor_count(self, obj):
        count = obj.doctors.count()
        return count

    doctor_count.short_description = 'Số bác sĩ'


class ServiceAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'specialty', 'price_display', 'duration',
        'appointment_count', 'active', 'created_date'
    ]
    list_filter = ['specialty', 'active', 'created_date']
    search_fields = ['name', 'description', 'specialty__name']
    list_editable = ['active']

    fieldsets = (
        ('Thông tin dịch vụ', {
            'fields': ('specialty', 'name', 'description')
        }),
        ('Giá & Thời gian', {
            'fields': (('price', 'duration'), 'image')
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

    price_display.short_description = 'Giá'

    def appointment_count(self, obj):
        count = obj.appointments.count()
        return count

    appointment_count.short_description = 'Lượt khám'


class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'active', 'appointment_today_count', 'created_date']
    list_filter = ['active']
    search_fields = ['name']

    def appointment_today_count(self, obj):
        today = timezone.now().date()
        count = obj.appointments.filter(date=today).count()
        return count

    appointment_today_count.short_description = 'Lịch hẹn hôm nay'


class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'employee_link', 'week_display', 'day_of_week_display',
        'time_display', 'shift_display', 'is_appointable', 'active'
    ]
    list_filter = ['day_of_week', 'shift', 'is_appointable', 'active', 'week_start']
    search_fields = ['employee__email', 'employee__first_name', 'employee__last_name']
    date_hierarchy = 'week_start'

    fieldsets = (
        ('Nhân viên', {
            'fields': ('employee',)
        }),
        ('Tuần làm việc', {
            'fields': (('week_start', 'week_end'), 'date', 'day_of_week')
        }),
        ('Thời gian', {
            'fields': (('start_time', 'end_time'), 'shift')
        }),
        ('Cài đặt', {
            'fields': ('is_appointable', 'active')
        }),
    )

    readonly_fields = ['week_end', 'shift']

    def employee_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.employee.id])
        return format_html('<a href="{}">{}</a>', url, obj.employee.get_full_name())

    employee_link.short_description = 'Nhân viên'

    def week_display(self, obj):
        return f"{obj.week_start.strftime('%d/%m')} - {obj.week_end.strftime('%d/%m/%Y')}"

    week_display.short_description = 'Tuần'

    def day_of_week_display(self, obj):
        return obj.get_day_of_week_display()

    day_of_week_display.short_description = 'Thứ'

    def time_display(self, obj):
        return f"{obj.start_time.strftime('%H:%M')} - {obj.end_time.strftime('%H:%M')}"

    time_display.short_description = 'Giờ'

    def shift_display(self, obj):
        colors = {
            'MORNING': 'orange',
            'AFTERNOON': 'green',
            'EVENING': 'blue',
            'NIGHT': 'purple'
        }
        color = colors.get(obj.shift, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_shift_display()
        )

    shift_display.short_description = 'Ca'


class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'doctor_link', 'patient_link', 'date',
        'time_display', 'status_display', 'type_display',
        'total_price_display', 'room'
    ]
    list_filter = [
        'status', 'type', 'date', 'doctor', 'room'
    ]
    search_fields = [
        'doctor__email', 'doctor__first_name', 'doctor__last_name',
        'patient__email', 'patient__first_name', 'patient__last_name'
    ]
    date_hierarchy = 'date'

    fieldsets = (
        ('Thông tin lịch hẹn', {
            'fields': (
                ('doctor', 'patient'),
                'services',
                ('date', 'start_time', 'end_time'),
            )
        }),
        ('Loại & Địa điểm', {
            'fields': (
                ('type', 'status'),
                'room',
                'meeting_link'
            )
        }),
        ('Ghi chú', {
            'fields': ('patient_note', 'doctor_note')
        }),
        ('Thanh toán', {
            'fields': ('total_price',)
        }),
        ('Thông tin khác', {
            'fields': (
                'work_schedule',
                'confirmed_date',
                'completed_date',
                'deleted_date',
                'reason'
            ),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['confirmed_date', 'completed_date']
    filter_horizontal = ['services']

    actions = ['confirm_appointments', 'cancel_appointments', 'complete_appointments']

    def doctor_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.doctor.id])
        return format_html('<a href="{}">{}</a>', url, obj.doctor.get_full_name())

    doctor_link.short_description = 'Bác sĩ'

    def patient_link(self, obj):
        if obj.patient:
            url = reverse('admin:users_user_change', args=[obj.patient.id])
            return format_html('<a href="{}">{}</a>', url, obj.patient.get_full_name())
        return format_html('<span style="color: gray;">Chưa có</span>')

    patient_link.short_description = 'Bệnh nhân'

    def time_display(self, obj):
        return f"{obj.start_time.strftime('%H:%M')} - {obj.end_time.strftime('%H:%M')}"

    time_display.short_description = 'Giờ'

    def status_display(self, obj):
        colors = {
            'PENDING': 'orange',
            'CONFIRMED': 'blue',
            'IN_PROCESS': 'purple',
            'COMPLETED': 'green',
            'CANCELLED': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )

    status_display.short_description = 'Trạng thái'

    def type_display(self, obj):
        icon = '💻' if obj.type == 'ONLINE' else '🏥'
        return format_html('{} {}', icon, obj.get_type_display())

    type_display.short_description = 'Loại'

    def total_price_display(self, obj):
        return format_html('<span style="color: green; font-weight: bold;">{} VNĐ</span>', obj.total_price)

    total_price_display.short_description = 'Tổng tiền'

    def confirm_appointments(self, request, queryset):
        updated = queryset.filter(status='PENDING').update(
            status='CONFIRMED',
            confirmed_date=timezone.now()
        )
        self.message_user(request, f'Đã xác nhận {updated} lịch hẹn')

    confirm_appointments.short_description = 'Xác nhận lịch hẹn'

    def cancel_appointments(self, request, queryset):
        updated = queryset.exclude(status='CANCELLED').update(
            status='CANCELLED',
            deleted_date=timezone.now()
        )
        self.message_user(request, f'Đã hủy {updated} lịch hẹn')

    cancel_appointments.short_description = 'Hủy lịch hẹn'

    def complete_appointments(self, request, queryset):
        updated = queryset.filter(status='IN_PROCESS').update(
            status='COMPLETED',
            completed_date=timezone.now()
        )
        self.message_user(request, f'Đã hoàn thành {updated} lịch hẹn')

    complete_appointments.short_description = 'Hoàn thành khám'


class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'doctor_link', 'patient_link', 'rating_display',
        'appointment_link', 'created_date'
    ]
    list_filter = ['rating', 'created_date']
    search_fields = [
        'doctor__email', 'doctor__first_name',
        'patient__email', 'patient__first_name'
    ]
    readonly_fields = ['appointment', 'created_date']

    fieldsets = (
        ('Thông tin đánh giá', {
            'fields': (
                'appointment',
                ('doctor', 'patient'),
                'rating',
                'comment'
            )
        }),
        ('Thời gian', {
            'fields': ('created_date',)
        }),
    )

    def doctor_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.doctor.id])
        return format_html('<a href="{}">{}</a>', url, obj.doctor.get_full_name())

    doctor_link.short_description = 'Bác sĩ'

    def patient_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.get_full_name())

    patient_link.short_description = 'Bệnh nhân'

    def rating_display(self, obj):
        stars = '⭐' * obj.rating
        return format_html('<span style="font-size: 16px;">{}</span>', stars)

    rating_display.short_description = 'Đánh giá'

    def appointment_link(self, obj):
        url = reverse('admin:clinic_appointment_change', args=[obj.appointment.id])
        return format_html('<a href="{}">Xem lịch hẹn</a>', url)

    appointment_link.short_description = 'Lịch hẹn'


admin_site.register(Review, ReviewAdmin)
admin_site.register(Appointment, AppointmentAdmin)
admin_site.register(WorkSchedule, WorkScheduleAdmin)
admin_site.register(Room, RoomAdmin)
admin_site.register(Specialty, SpecialtyAdmin)
admin_site.register(Service, ServiceAdmin)