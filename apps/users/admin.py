from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from apps.users.models import User, PatientProfile, DoctorProfile, NurseProfile, PharmacistProfile, UserRole, \
    EmployeeRole
from clinic_management.admin import admin_site


class PatientProfileInline(admin.StackedInline):
    model = PatientProfile
    can_delete = False
    verbose_name = 'Hồ sơ bệnh nhân'
    verbose_name_plural = 'Hồ sơ bệnh nhân'
    fields = [
        'patient_code', 'blood_type', 'height', 'weight',
        'allergies', 'chronic_diseases', 'medical_history',
        'insurance_number', 'registered_date'
    ]
    readonly_fields = ['patient_code', 'registered_date']


class DoctorProfileInline(admin.StackedInline):
    model = DoctorProfile
    can_delete = False
    verbose_name = 'Hồ sơ bác sĩ'
    verbose_name_plural = 'Hồ sơ bác sĩ'
    fields = [
        'specialty', 'doctor_license', 'degree', 'experience_years',
        'bio', 'consultation_fee', 'salary',
        ('rating', 'total_reviews', 'total_patients'),
        'is_available'
    ]
    readonly_fields = ['rating', 'total_reviews', 'total_patients']


class NurseProfileInline(admin.StackedInline):
    model = NurseProfile
    can_delete = False
    verbose_name = 'Hồ sơ y tá'
    verbose_name_plural = 'Hồ sơ y tá'
    fields = ['nurse_license', 'degree', 'experience_years', 'salary']


class PharmacistProfileInline(admin.StackedInline):
    model = PharmacistProfile
    can_delete = False
    verbose_name = 'Hồ sơ dược sĩ'
    verbose_name_plural = 'Hồ sơ dược sĩ'
    fields = ['pharmacist_license', 'degree', 'experience_years', 'salary']


class UserAdmin(BaseUserAdmin):
    list_display = [
        'email', 'full_name_display', 'user_role_display',
        'employee_role_display', 'avatar_display', 'is_active',
        'date_joined'
    ]
    list_filter = ['user_role', 'employee_role', 'is_active', 'date_joined', 'gender']
    search_fields = ['email', 'first_name', 'last_name', 'phone', 'employee_id']
    ordering = ['-date_joined']

    fieldsets = (
        ('Thông tin đăng nhập', {
            'fields': ('email', 'password')
        }),
        ('Thông tin cá nhân', {
            'fields': (
                ('first_name', 'last_name'),
                'date_of_birth', 'gender', 'phone',
                'address', 'avatar'
            )
        }),
        ('Vai trò', {
            'fields': (
                ('user_role', 'employee_role'),
                ('employee_id', 'hire_date')
            )
        }),
        ('Quyền hạn', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Thông tin khác', {
            'fields': ('last_login', 'date_joined', 'updated_date', 'fcm_token'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        ('Tạo tài khoản mới', {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2',
                'first_name', 'last_name',
                'user_role', 'employee_role'
            ),
        }),
    )

    readonly_fields = ['last_login', 'date_joined', 'updated_date']
    filter_horizontal = ['groups', 'user_permissions']

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []

        inlines = []
        if obj.user_role == UserRole.PATIENT:
            inlines.append(PatientProfileInline)
        elif obj.user_role == UserRole.EMPLOYEE:
            if obj.employee_role == EmployeeRole.DOCTOR:
                inlines.append(DoctorProfileInline)
            elif obj.employee_role == EmployeeRole.NURSE:
                inlines.append(NurseProfileInline)
            elif obj.employee_role == EmployeeRole.PHARMACIST:
                inlines.append(PharmacistProfileInline)

        return [inline(self.model, self.admin_site) for inline in inlines]

    def full_name_display(self, obj):
        return obj.get_full_name()

    full_name_display.short_description = 'Họ tên'

    def user_role_display(self, obj):
        colors = {
            'Admin': 'red',
            'Patient': 'green',
            'Employee': 'blue'
        }
        color = colors.get(obj.user_role, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_user_role_display()
        )

    user_role_display.short_description = 'Vai trò'

    def employee_role_display(self, obj):
        if obj.employee_role:
            return obj.get_employee_role_display()
        return '-'

    employee_role_display.short_description = 'Chức vụ'

    def avatar_display(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius: 50%;" />',
                obj.avatar.url
            )
        return '❌'

    avatar_display.short_description = 'Avatar'

    actions = ['activate_users', 'deactivate_users']

    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Đã kích hoạt {updated} tài khoản')

    activate_users.short_description = 'Kích hoạt tài khoản'

    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Đã vô hiệu hóa {updated} tài khoản')

    deactivate_users.short_description = 'Vô hiệu hóa tài khoản'


class PatientProfileAdmin(admin.ModelAdmin):
    list_display = [
        'patient_code', 'user_link', 'blood_type',
        'height', 'weight', 'bmi_display', 'registered_date'
    ]
    list_filter = ['blood_type', 'registered_date']
    search_fields = ['patient_code', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['patient_code', 'registered_date', 'bmi_display']

    fieldsets = (
        ('Thông tin bệnh nhân', {
            'fields': ('user', 'patient_code', 'registered_date')
        }),
        ('Chỉ số sức khỏe', {
            'fields': (
                'blood_type',
                ('height', 'weight', 'bmi_display')
            )
        }),
        ('Tiền sử bệnh', {
            'fields': ('allergies', 'chronic_diseases', 'medical_history')
        }),
        ('Bảo hiểm', {
            'fields': ('insurance_number',)
        }),
    )

    def user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())

    user_link.short_description = 'Bệnh nhân'

    def bmi_display(self, obj):
        if obj.height and obj.weight:
            height_m = float(obj.height) / 100
            bmi = float(obj.weight) / (height_m ** 2)

            # BMI classification
            if bmi < 18.5:
                color, status = 'orange', 'Thiếu cân'
            elif 18.5 <= bmi < 25:
                color, status = 'green', 'Bình thường'
            elif 25 <= bmi < 30:
                color, status = 'orange', 'Thừa cân'
            else:
                color, status = 'red', 'Béo phì'

            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f} ({})</span>',
                color, bmi, status
            )
        return '-'

    bmi_display.short_description = 'BMI'


class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'specialty', 'doctor_license',
        'rating_display', 'total_patients', 'consultation_fee',
        'is_available'
    ]
    list_filter = ['specialty', 'is_available', 'rating']
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'doctor_license'
    ]
    readonly_fields = ['rating', 'total_reviews', 'total_patients']

    fieldsets = (
        ('Thông tin bác sĩ', {
            'fields': (
                'user', 'specialty', 'doctor_license',
                'degree', 'experience_years'
            )
        }),
        ('Thông tin nghề nghiệp', {
            'fields': ('bio', 'consultation_fee', 'salary')
        }),
        ('Đánh giá & Thống kê', {
            'fields': (
                ('rating', 'total_reviews'),
                'total_patients',
                'is_available'
            )
        }),
    )

    def user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())

    user_link.short_description = 'Bác sĩ'

    def rating_display(self, obj):
        stars = '⭐' * int(obj.rating)
        return format_html(
            '{} <small>({}/5.0 - {} đánh giá)</small>',
            stars, obj.rating, obj.total_reviews
        )

    rating_display.short_description = 'Đánh giá'


class NurseProfileAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'nurse_license', 'degree', 'experience_years', 'salary']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'nurse_license']

    def user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())

    user_link.short_description = 'Y tá'


class PharmacistProfileAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'pharmacist_license', 'degree', 'experience_years', 'salary']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'pharmacist_license']

    def user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())

    user_link.short_description = 'Dược sĩ'


admin_site.register(PharmacistProfile, PharmacistProfileAdmin)
admin_site.register(NurseProfile, NurseProfileAdmin)
admin_site.register(DoctorProfile, DoctorProfileAdmin)
admin_site.register(PatientProfile, PatientProfileAdmin)
admin_site.register(User, UserAdmin)
