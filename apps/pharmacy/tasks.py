from celery import shared_task
from django.utils import timezone


@shared_task
def auto_commit_daily_report():
    today = timezone.now().date()
    print(f"[Celery] Bắt đầu chốt sổ kho ngày {today}...")

    # 1. Gọi service để tính toán số liệu
    report = generate_daily_report(date=today)

    # 2. Logic chốt sổ tự động
    # Nếu dược sĩ chưa chốt tay, hệ thống sẽ chốt dùm
    if not report.is_committed:
        report.is_committed = True
        report.save()

        # [QUAN TRỌNG] Cập nhật lại tồn kho Medicine theo số liệu chốt
        # Để đảm bảo ngày mai bắt đầu với số chính xác
        for detail in report.details.all():
            med = detail.medicine
            # Nếu chạy tự động, ta tin tưởng số liệu máy tính (system calc)
            # trừ khi dược sĩ đã nhập actual_quantity trước đó
            if detail.actual_quantity == 0 and detail.export_quantity == 0 and detail.import_quantity == 0:
                # Trường hợp thuốc ko động chạm gì thì thôi
                pass
            else:
                med.current_stock = detail.actual_quantity
                med.save()

        return f"Đã chốt sổ thành công ngày {today}"

    return f"Ngày {today} đã được dược sĩ chốt trước đó. Không làm gì cả."