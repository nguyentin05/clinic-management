from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


class NotificationType(models.TextChoices):
    APPOINTMENT_CREATED = 'APPOINTMENT_CREATED', 'Lịch hẹn mới được tạo'
    APPOINTMENT_CONFIRMED = 'APPOINTMENT_CONFIRMED', 'Lịch hẹn được xác nhận'
    APPOINTMENT_CANCELLED = 'APPOINTMENT_CANCELLED', 'Lịch hẹn bị hủy'
    APPOINTMENT_REMINDER = 'APPOINTMENT_REMINDER', 'Nhắc nhở lịch hẹn'
    APPOINTMENT_STARTED = 'APPOINTMENT_STARTED', 'Lịch hẹn đã bắt đầu'
    APPOINTMENT_COMPLETED = 'APPOINTMENT_COMPLETED', 'Lịch hẹn hoàn thành'

    TEST_ORDER_REQUESTED = 'TEST_ORDER_REQUESTED', 'Xét nghiệm đã được chỉ định'
    TEST_ORDER_PROCESSING = 'TEST_ORDER_PROCESSING', 'Xét nghiệm đang được xử lý'
    TEST_ORDER_COMPLETED = 'TEST_ORDER_COMPLETED', 'Kết quả xét nghiệm đã có'
    TEST_ORDER_CANCELLED = 'TEST_ORDER_CANCELLED', 'Xét nghiệm bị hủy'

    PRESCRIPTION_CREATED = 'PRESCRIPTION_CREATED', 'Đơn thuốc đã được bác sĩ kê'
    PRESCRIPTION_COMPLETED = 'PRESCRIPTION_COMPLETED', 'Đơn thuốc đã hoàn tất'

    PAYMENT_CREATED = 'PAYMENT_CREATED', 'Thanh toán mới được tạo'
    PAYMENT_SUCCESS = 'PAYMENT_SUCCESS', 'Thanh toán thành công'
    PAYMENT_FAILED = 'PAYMENT_FAILED', 'Thanh toán thất bại'

    SCHEDULE_CONFIRMED = 'SCHEDULE_CONFIRMED', 'Lịch làm việc đã được xác nhận'
    SYSTEM_ANNOUNCEMENT = 'SYSTEM_ANNOUNCEMENT', 'Thông báo hệ thống'

class Notification(models.Model):
    recipient = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=50, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.IntegerField(null=True, blank=True)

    #trường nâng cao khóa ngoại đa năng dùng để lấy object
    related_object = GenericForeignKey('content_type', 'object_id')

    action_url = models.CharField(max_length=500, blank=True)

    is_read = models.BooleanField(default=False)

    metadata = models.JSONField(default=dict, blank=True)

    created_date = models.DateTimeField(auto_now_add=True)

    is_deleted = models.BooleanField(default=False)
    deleted_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['recipient', '-created_date']),
            models.Index(fields=['recipient', 'is_read', '-created_date']),
            models.Index(fields=['type', '-created_date']),
        ]

    def __str__(self):
        return f"{self.recipient.get_full_name()} - {self.get_type_display()}"

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_date = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_date'])