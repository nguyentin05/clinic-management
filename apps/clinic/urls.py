from clinic_management.urls import router

from apps.clinic.views import SpecialtyView, ServiceView, WorkScheduleView, AppointmentView

router.register('specialties', SpecialtyView, basename='specialty')
router.register('services', ServiceView, basename='service')
router.register('schedules', WorkScheduleView, basename='work-schedule')
router.register('appointments', AppointmentView, basename='appointments')

urlpatterns = [

]