from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from firebase_admin import messaging

from apps.clinic.models import AppointmentType
from apps.notifications.models import Notification, NotificationType
from apps.notifications.serializers import NotificationWebSocketSerializer


class NotificationService:
    # gửi tbao 1 ng
    @staticmethod
    def create_notification(recipient, notification_type, title, message,
                            data, send_push=True):
        try:
            notification = Notification.objects.create(
                recipient=recipient,
                type=notification_type,
                title=title,
                message=message,
                data=data or {}
            )

            if send_push and hasattr(recipient, 'fcm_token'):
                NotificationService.send_firebase(recipient.fcm_token, title, message, data or {})

            NotificationService.send_websocket(recipient.id, notification)

            return notification

        except Exception as e:
            print(str(e))
            return None

    # gửi tbao nhiều ng
    @staticmethod
    def create_notifications(recipients, notification_type, title, message, data):
        try:
            notifications = []
            fcm_tokens = []

            for recipient in recipients:
                notification = Notification.objects.create(
                    recipient=recipient,
                    type=notification_type,
                    title=title,
                    message=message,
                    data=data or {}
                )
                notifications.append(notification)

                if hasattr(recipient, 'fcm_token'):
                    fcm_tokens.append(recipient.fcm_token)

            if fcm_tokens:
                NotificationService.send_firebase_multicast(fcm_tokens, title, message, data or {})

            return notifications

        except Exception as e:
            print(str(e))
            return None

    # gửi 1 message cho firebase
    @staticmethod
    def send_firebase(token, title, body, data):
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={str(k): str(v) for k, v in data.items()},
                token=token,
                # cấu hình tùy điện thoại
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound='default',
                        priority='high',
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1,
                        )
                    )
                )
            )
            messaging.send(message)

        except messaging.UnregisteredError:
            print(f"FCM token chưa đăng ký: {token}")
        except Exception as e:
            print(str(e))

    # gửi message websocket
    @staticmethod
    def send_websocket(user_id, notification):
        try:
            channel_layer = get_channel_layer()

            async_to_sync(channel_layer.group_send)(
                f"notifications_{user_id}",
                {
                    "type": "notification_message",
                    "notification": NotificationWebSocketSerializer.serialize(notification)
                }
            )
        except Exception as e:
            print(str(e))

    # gửi n message cho firebase
    @staticmethod
    def send_firebase_multicast(tokens, title, body, data):
        try:
            messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data={str(k): str(v) for k, v in data.items()},
                tokens=tokens,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound='default',
                        priority='high',
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1,
                        )
                    )
                )
            )

        except messaging.UnregisteredError:
            print("Có FCM token chưa đăng ký")
        except Exception as e:
            print(str(e))

    # đánh dấu đã đọc
    @staticmethod
    def mark_as_read(notification_id, user):
        try:
            Notification.objects.get(id=notification_id, recipient=user).update(is_read=True)
            return True
        except Notification.DoesNotExist:
            return False

    # get sl chưa đọc
    @staticmethod
    def get_unread_count(user):
        return Notification.objects.filter(recipient=user, is_read=False).count()


# thông báo về lịch hẹn
class AppointmentNotifications:
    @staticmethod
    def notify_created(appointment):
        NotificationService.create_notification(
            recipient=appointment.doctor,
            notification_type=NotificationType.APPOINTMENT_CREATED,
            title="Lịch hẹn mới",
            message=f"Bạn có lịch hẹn mới!"
                    f"{appointment.date.strftime('%d/%m/%Y')} ({appointment.start_time.strftime('%H:%M')}:{appointment.end_time.strftime('%H:%M')})",
            data={
                'appointment_id': appointment.id,
                'screen': 'AppointmentDetail',
            }
        )

        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type=NotificationType.APPOINTMENT_CREATED,
            title="Đặt lịch hẹn thành công",
            message=f"Lịch hẹn của bạn với bác sĩ {appointment.doctor.get_full_name()} "
                    f"{appointment.date.strftime('%d/%m/%Y')} ({appointment.start_time.strftime('%H:%M')}:{appointment.end_time.strftime('%H:%M')})"
                    f"đang chờ xác nhận.",
            data={
                'appointment_id': appointment.id,
                'screen': 'AppointmentDetail',
            }
        )

    @staticmethod
    def notify_confirmed(appointment):
        if appointment.type == AppointmentType.ONLINE:
            message = (f"Lịch hẹn của bạn với bác sĩ {appointment.doctor.get_full_name()}\n"
                       f"{appointment.date.strftime('%d/%m/%Y')} ({appointment.start_time.strftime('%H:%M')}:{appointment.end_time.strftime('%H:%M')})"
                       "đã được xác nhận."
                       f"Link meeting: {appointment.meeting_link}")
            data = {
                'appointment_id': appointment.id,
                'screen': 'AppointmentDetail',
                'meeting_link': appointment.meeting_link
            }
        else:
            message = (f"Lịch hẹn của bạn với bác sĩ {appointment.doctor.get_full_name()}\n"
                       f"{appointment.date.strftime('%d/%m/%Y')} ({appointment.start_time.strftime('%H:%M')}:{appointment.end_time.strftime('%H:%M')})"
                       "đã được xác nhận."
                       f"Số phòng: {appointment.room.name}")
            data = {
                'appointment_id': appointment.id,
                'screen': 'AppointmentDetail',
                'room': appointment.room.name
            }

        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="Lịch hẹn đã được xác nhận",
            message=message,
            data=data
        )

    @staticmethod
    def notify_cancelled(appointment):
        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type=NotificationType.APPOINTMENT_CANCELLED,
            title="Lịch hẹn bị hủy",
            message=f"Lịch hẹn của bạn với bác sĩ {appointment.doctor.get_full_name()}"
                    f"{appointment.date.strftime('%d/%m/%Y')} ({appointment.start_time.strftime('%H:%M')}:{appointment.end_time.strftime('%H:%M')})"
                    f"Lý do: {appointment.reason}"
                    f"Xin lỗi bạn vì sự bất tiện trên.",
            data={
                'appointment_id': appointment.id,
                'screen': 'AppointmentDetail',
            }
        )

    @staticmethod
    def notify_started(appointment):
        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type=NotificationType.APPOINTMENT_STARTED,
            title="Lịch hẹn đang bắt đầu",
            message=f"Bác sĩ {appointment.doctor.get_full_name()} đã bắt đầu khám bệnh cho bạn.",
            data={
                'appointment_id': appointment.id,
                'screen': 'AppointmentDetail',
            }
        )

    @staticmethod
    def notify_completed(appointment):
        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type=NotificationType.APPOINTMENT_COMPLETED,
            title="Lịch hẹn đã hoàn thành",
            message=f"Lịch hẹn của bạn với bác sĩ {appointment.doctor.get_full_name()} đã hoàn thành. "
                    f"Cảm ơn bạn đã sử dụng dịch vụ.",
            data={
                'appointment_id': appointment.id,
                'screen': 'AppointmentDetail',
            }
        )

    @staticmethod
    def notify_reminder(appointment):
        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type=NotificationType.APPOINTMENT_REMINDER,
            title="Nhắc nhở lịch hẹn",
            message=(f"Lịch hẹn của bạn với bác sĩ {appointment.doctor.get_full_name()}"
                     f"{appointment.date.strftime('%d/%m/%Y')} ({appointment.start_time.strftime('%H:%M')}:{appointment.end_time.strftime('%H:%M')})"
                     "còn 2 tiếng nữa, vui lòng đúng giờ hẹn."),
            data={
                'appointment_id': appointment.id,
                'screen': 'AppointmentDetail',
            }
        )


# thông báo về xét nghiệm
class TestOrderNotifications:
    @staticmethod
    def notify_created(test_order):
        appointment = test_order.medical_record.appointment

        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type=NotificationType.TEST_ORDER_REQUESTED,
            title="Xét nghiệm mới được chỉ định",
            message=f"Bác sĩ {appointment.doctor.get_full_name()} đã chỉ định "
                    f"xét nghiệm {test_order.service.name} cho bạn.",
            data={
                'appointment_id': appointment.id,
                'test_order_id': test_order.id,
                'screen': 'MedicalRecord',
            }
        )

    @staticmethod
    def notify_completed(test_order):
        appointment = test_order.medical_record.appointment

        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type=NotificationType.TEST_ORDER_COMPLETED,
            title="Kết quả xét nghiệm đã có",
            message=f"Kết quả xét nghiệm {test_order.service.name} của bạn đã có. "
                    f"Vui lòng xem chi tiết trong hồ sơ bệnh án.",
            data={
                'appointment_id': appointment.id,
                'test_order_id': test_order.id,
                'screen': 'MedicalRecord',
            }
        )

    @staticmethod
    def notify_cancelled(test_order):
        appointment = test_order.medical_record.appointment

        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type=NotificationType.TEST_ORDER_CANCELLED,
            title="Xét nghiệm đã bị hủy",
            message=f"Xét nghiệm {test_order.service.name} của bạn đã bị hủy."
                    f"Lý do: {test_order.reason}"
                    f"Xin lỗi bạn vì sự bất tiện trên.",
            data={
                'appointment_id': appointment.id,
                'test_order_id': test_order.id,
                'screen': 'MedicalRecord',
            }
        )

    @staticmethod
    def notify_processing(test_order):
        appointment = test_order.medical_record.appointment

        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type=NotificationType.TEST_ORDER_PROCESSING,
            title="Xét nghiệm đang được xử lý",
            message=f"Xét nghiệm {test_order.service.name} của bạn đang được xử lý.\n"
                    f"Vui lòng chờ cho đến khi có được kết quả",
            data={
                'appointment_id': appointment.id,
                'test_order_id': test_order.id,
                'screen': 'MedicalRecord',
            }
        )


class PrescriptionNotifications:
    @staticmethod
    def notify_created(prescription):
        appointment = prescription.appointment

        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type=NotificationType.PRESCRIPTION_CREATED,
            title="Đơn thuốc đã được kê",
            message=f"Bác sĩ {appointment.doctor.get_full_name()} đã kê đơn thuốc cho bạn. "
                    f"Vui lòng xem chi tiết và thực hiện theo hướng dẫn.",
            data={
                'appointment_id': appointment.id,
                'prescription_id': prescription.id,
                'screen': 'Prescription',
            }
        )

    @staticmethod
    def notify_completed(prescription):
        appointment = prescription.appointment

        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type=NotificationType.PRESCRIPTION_COMPLETED,
            title="Đơn thuốc đã hoàn tất",
            message="Dược sĩ đã soạn xong đơn thuốc cho bạn.\n"
                    "Vui lòng đến quầy để nhận thuốc",
            data={
                'appointment_id': appointment.id,
                'prescription_id': prescription.id,
                'screen': 'Prescription',
            }
        )


class PaymentNotifications:
    @staticmethod
    def notify_created(payment):
        amount = f"{payment.amount:,.0f}".replace(',', '.')
        message = ''
        screen = 'AppointmentDetail'

        if payment.appointment:
            message = (f"Bạn có hóa đơn thanh toán lịch khám với bác sĩ {payment.appointment.doctor.get_full_name()}\n"
                       f"với số tiền {amount} VNĐ.\n"
                       f"Mã thanh toán: {payment.id}")
        elif payment.get_prescription:
            message = (f"Bạn có hóa đơn thanh toán đơn thuốc\n"
                       f"với số tiền {amount} VNĐ.\n"
                       f"Mã thanh toán: {payment.id}")
            screen = 'Prescription'  # sửa lại cho đúng screen

        NotificationService.create_notification(
            recipient=payment.patient,
            notification_type=NotificationType.PAYMENT_CREATED,
            title="Hóa đơn thanh toán mới",
            message=message,
            data={
                'payment_id': payment.id,
                'amount': str(payment.amount),
                'appointment_id': payment.appointment_id if payment.appointment else None,
                'prescription_id': payment.prescription_id if payment.prescription else None,
                'screen': screen,
            }
        )

    @staticmethod
    def notify_completed(payment):
        amount = f"{payment.amount:,.0f}".replace(',', '.')
        message = ''

        if payment.appointment:
            message = (f"Bạn đã thanh toán thành công {amount} VNĐ\n"
                       f"cho lịch khám với bác sĩ {payment.appointment.doctor.get_full_name()}\n"
                       f"bằng phương thức {payment.get_method_display()}.\n"
                       f"Mã giao dịch: {payment.id}")
        elif payment.prescription:
            message = (f"Bạn đã thanh toán thành công {amount} VNĐ\n"
                       f"cho đơn thuốc\n"
                       f"bằng phương thức {payment.get_method_display()}.\n"
                       f"Mã giao dịch: {payment.id}")

        NotificationService.create_notification(
            recipient=payment.patient,
            notification_type=NotificationType.PAYMENT_COMPLETED,
            title="Thanh toán thành công",
            message=message,
            data={
                'payment_id': payment.id,
                'amount': str(payment.amount),
                'method': payment.method,
                'appointment_id': payment.appointment_id if payment.appointment else None,
                'prescription_id': payment.prescription_id if payment.get_prescription else None,
                'screen': 'PaymentDetail',
            }
        )

# class SystemNotifications:
#     @staticmethod
#     def notify_system_announcement(users, title, message):
#         NotificationService.create_notifications(recipients=users,
#                                                  notification_type=NotificationType.SYSTEM_ANNOUNCEMENT, title=title,
#                                                  message=message, data={'screen': 'Home'})
