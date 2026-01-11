from django.contrib import admin
from django.db.models.functions import ExtractYear, TruncMonth
from django.urls import path
from django.template.response import TemplateResponse
from django.db.models import Count, Sum, Avg, Max, Min, Q, F
from django.utils import timezone
from datetime import timedelta
from apps.clinic.models import Appointment, AppointmentStatus, Service
from apps.medical.models import MedicalRecord, TestOrder, TestStatus
from apps.payment.models import Payment, PaymentMethod
from apps.users.models import User, UserRole, Gender, PatientProfile


class MyClinicAdminSite(admin.AdminSite):
    site_header = 'Quản trị Phòng khám'

    def get_urls(self):
        urls = [
            path('patient-stats/', self.patient_stats_view),
            path('service-stats/', self.service_stats_view),
            path('disease-stats/', self.disease_stats_view),
            path('revenue-stats/', self.revenue_stats_view),
        ]
        return urls + super().get_urls()

    def patient_stats_view(self, request):
        total_patients = User.objects.filter(user_role=UserRole.PATIENT).count()

        current_year = timezone.now().year

        patients = User.objects.filter(user_role=UserRole.PATIENT, date_of_birth__isnull=False).annotate(
            age=current_year - ExtractYear('date_of_birth'))

        age_groups_data = patients.aggregate(
            group_0_17=Count('id', filter=Q(age__lte=17)),
            group_18_30=Count('id', filter=Q(age__gte=18, age__lte=30)),
            group_31_45=Count('id', filter=Q(age__gte=31, age__lte=45)),
            group_46_60=Count('id', filter=Q(age__gte=46, age__lte=60)),
            group_61_75=Count('id', filter=Q(age__gte=61, age__lte=75)),
            group_76_plus=Count('id', filter=Q(age__gte=76))
        )

        labels = {
            'group_0_17': '0-17',
            'group_18_30': '18-30',
            'group_31_45': '31-45',
            'group_46_60': '46-60',
            'group_61_75': '61-75',
            'group_76_plus': '76+'
        }

        age_stats = []

        for key, count in age_groups_data.items():
            age_stats.append({
                'age_group': labels.get(key, key),
                'count': count
            })

        gender_stats = []

        for gender in Gender.choices:
            count = User.objects.filter(user_role=UserRole.PATIENT, gender=gender[0]).count()
            gender_stats.append({
                'gender': gender[0],
                'gender_display': gender[1],
                'count': count
            })

        # dùng chuyên khoa của bác sĩ để xác định
        specialty_stats = Appointment.objects.filter(
            status=AppointmentStatus.COMPLETED,
            doctor__doctor_profile__specialty__isnull=False
        ).values(specialty_name=F('doctor__doctor_profile__specialty__name')) \
            .annotate(count=Count('id')).order_by('-count')

        stats = {
            'total_patients': total_patients,
            'age_stats': age_stats,
            'gender_stats': gender_stats,
            'specialty_stats': specialty_stats,
        }

        return TemplateResponse(request, 'admin/patient_stats.html', stats)

    def service_stats_view(self, request):
        total_services = Service.objects.filter(active=True).count()

        services_stats = Service.objects.filter(active=True).annotate(
            appointment_use=Count('appointments', filter=Q(appointments__status=AppointmentStatus.COMPLETED)),
            test_order_use=Count('test_orders_service', filter=Q(test_orders_service__status=TestStatus.COMPLETED))
        ).annotate(
            total_use=F('appointment_use') + F('test_order_use')
        ).order_by('-total_use')

        total_use = services_stats.aggregate(total=Sum('total_use'))
        total_use = total_use['total'] or 0

        specialties = {}

        for s in services_stats:
            specialty = s.specialty.name
            if specialty not in specialties:
                specialties[specialty] = {
                    'specialty': specialty,
                    'service_count': 0,
                    'usage_count': 0,
                }

            specialties[specialty]['service_count'] += 1
            specialties[specialty]['usage_count'] += s.total_use

        specialty_stats = list(specialties.values())


        context = {
            'total_services': total_services,
            'total_use': total_use,
            'specialty_stats': specialty_stats,
            'services_stats': services_stats,
        }

        return TemplateResponse(request, 'admin/service_stats.html', context)

    def disease_stats_view(self, request):
        last_30_days = timezone.now().date() - timedelta(days=30)

        medicals = MedicalRecord.objects.filter(appointment__date__gte=last_30_days)

        total_records = medicals.count()

        stats_by_specialty = medicals.values(
            name=F('appointment__doctor__doctor_profile__specialty__name')
        ).annotate(
            count=Count('appointment_id')
        ).order_by('-count')

        recent_diagnoses = medicals.exclude(diagnosis='').values(
            'diagnosis',
            'appointment__date',
            doctor_last_name=F('appointment__doctor__last_name'),
            doctor_first_name=F('appointment__doctor__first_name')
        ).order_by('-appointment__date')[:10]

        context = {
            'total_records': total_records,
            'stats_by_specialty': stats_by_specialty,
            'recent_diagnoses': recent_diagnoses
        }

        return TemplateResponse(request, 'admin/disease_stats.html', context)

    def revenue_stats_view(self, request):
        current_year = timezone.now().year

        totals = Payment.objects.filter(is_paid=True).aggregate(
            total=Sum('amount'),
            from_appt=Sum('amount', filter=Q(appointment__isnull=False)),
            from_med=Sum('amount', filter=Q(prescription__isnull=False))
        )

        monthly_stats = Payment.objects.filter(
            is_paid=True,
            paid_date__year=current_year
        ).annotate(
            month=TruncMonth('paid_date')
        ).values('month').annotate(
            revenue=Sum('amount')
        ).order_by('month')

        monthly_data = []
        temp_map = {item['month'].month: item['revenue'] for item in monthly_stats}

        for i in range(1, 13):
            monthly_data.append({
                'month': f'T{i}',
                'revenue': temp_map.get(i, 0)
            })

        services_data = Service.objects.filter(active=True).annotate(
            appt_use=Count('appointments', filter=Q(appointments__status=AppointmentStatus.COMPLETED)),
            test_use=Count('test_orders_service', filter=Q(test_orders_service__status=TestStatus.COMPLETED))
        ).annotate(
            total_use=F('appt_use') + F('test_use')
        ).annotate(
            revenue=F('total_use') * F('price')
        ).order_by('-revenue')[:10]

        specialty_data = Appointment.objects.filter(
            status=AppointmentStatus.COMPLETED
        ).values(
            name=F('doctor__doctor_profile__specialty__name')
        ).annotate(
            revenue=Sum('total_price')
        ).order_by('-revenue')

        context = {
            'current_year': current_year,
            'totals': totals,
            'monthly_data': monthly_data,
            'services_data': services_data,
            'specialty_data': specialty_data,
        }

        return TemplateResponse(request, 'admin/revenue_stats.html', context)


admin_site = MyClinicAdminSite(name='clinic_admin')
