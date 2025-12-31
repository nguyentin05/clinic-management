from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.contrib import admin

from apps.clinic.models import Specialty, Service

class ServiceForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorUploadingWidget)

    class Meta:
        model = Service
        fields = '__all__'

class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_date', 'active']
    list_display_links = ['id', 'name']
    search_fields = ['name']

class ServiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_date', 'active', 'specialty']
    list_display_links = ['id', 'name']
    list_filter = ['specialty']
    search_fields = ['name']
    form = ServiceForm

admin.site.register(Specialty, SpecialtyAdmin)
admin.site.register(Service, ServiceAdmin)

