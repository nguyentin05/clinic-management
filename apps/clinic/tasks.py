from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import WorkSchedule
from apps.users.models import User, UserRole


@shared_task
def auto_clone_schedule():
    #hôm nay là thứ 2
    today = timezone.now().date()

    next_monday = today + timedelta(days=7)
    next_sunday = next_monday + timedelta(days=6)

    employees = User.objects.filter(is_active=True, user_role=UserRole.EMPLOYEE)

    for employee in employees:
        current = WorkSchedule.objects.filter(
            employee=employee,
            from_date=today,
            active=True
        )

        if current:
            WorkSchedule.objects.filter(
                employee=employee,
                from_date=next_monday
            ).delete()

            new_schedules = []

            for schedule in current:
                ws = WorkSchedule(
                    employee=schedule.employee,
                    day_of_week=schedule.day_of_week,
                    start_time=schedule.start_time,
                    end_time=schedule.end_time,
                    shift=schedule.shift,
                    is_appointable=schedule.is_appointable,
                    from_date=next_monday,
                    to_date=next_sunday,
                    active=True
                )
                new_schedules.append(ws)


            WorkSchedule.objects.bulk_create(new_schedules)

    print("✅ Đã xong")