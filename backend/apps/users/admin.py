from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import User

class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'role']
    list_display_links = ['id', 'email']
    list_filter = ['is_staff', 'is_active', 'role']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['avatar_view']

    def avatar_view(self, user):
        if user.avatar:
            return mark_safe(f'<img src="{user.avatar.url}" width="200" />')

admin.site.register(User, UserAdmin)
