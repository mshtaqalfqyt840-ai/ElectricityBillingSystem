"""
api/services/notification_service.py
خدمة الاشعارات — تتبع نفس نمط meter_service.py

NotificationService:
    مسؤولة عن انشاء سجلات الاشعارات في قاعدة البيانات وتسجيلها في Logger.
    مصممة للتوسع: يمكن اضافة قنوات ارسال (SMS/WhatsApp/Email) مستقبلا
    دون تغيير منطق المهمة المجدولة (tasks.py).
"""
import logging
from ..models import Invoice, Notification, Student
from .notification_channel_service import NotificationChannelService

logger = logging.getLogger(__name__)

CRITICAL_WARNING_TEXT = (
    "إنذار حرج وأخير: لم يتبقَّ سوى 5 ساعات على انتهاء مهلة سداد فاتورة الكهرباء "
    "لغرفتكم. يرجى المسارعة بالسداد لتفادي فصل التيار آلياً."
)

AUTO_DISCONNECT_TEXT = (
    "تم فصل التيار آلياً نظراً لانتهاء مهلة السداد للفاتورة. يرجى المبادرة بالسداد لإعادة الخدمة."
)


class NotificationService:
    """
    خدمة انشاء الاشعارات وحفظها.

    الاستخدام:
        NotificationService.send_critical_warning(invoice)
        NotificationService.send_auto_disconnect(invoice)
    """

    @classmethod
    def send_critical_warning(cls, invoice: "Invoice") -> "Notification":
        """
        ينشئ سجل اشعار حرج لفاتورة اقتربت من انتهاء مهلة السداد.
        يُرجع كائن Notification المنشأ.
        """
        notification = Notification.objects.create(
            invoice           = invoice,
            room              = invoice.room,
            notification_type = "critical_warning",
            message           = CRITICAL_WARNING_TEXT,
        )
        logger.info(
            "[NotificationService] critical_warning sent — invoice_id=%s room=%s",
            invoice.id, invoice.room,
        )

        # إرسال SMS/WhatsApp للطلاب النشطين في الغرفة
        active_students = Student.objects.filter(room=invoice.room, status='active')
        sms_success_count = 0
        sms_attempted = False

        for student in active_students:
            if student.phone:
                sms_attempted = True
                try:
                    success = NotificationChannelService.send_sms(student.phone, CRITICAL_WARNING_TEXT)
                    if success:
                        sms_success_count += 1
                except Exception as exc:
                    logger.error(
                        "[NotificationService] تعذر إرسال رسالة SMS/واتساب، سيبقى الإشعار الداخلي فعالاً: %s", exc
                    )

        if sms_attempted:
            if sms_success_count > 0:
                notification.sms_status = 'sent'
            else:
                notification.sms_status = 'failed'
                logger.error("[NotificationService] تعذر إرسال رسالة SMS/واتساب لجميع الطلاب، سيبقى الإشعار الداخلي فعالاً")
            notification.save(update_fields=['sms_status'])

        return notification

    @classmethod
    def send_auto_disconnect(cls, invoice: "Invoice") -> "Notification":
        """
        ينشئ سجل اشعار فصل آلي لفاتورة انتهت مهلة سدادها.
        يُرجع كائن Notification المنشأ.
        """
        notification = Notification.objects.create(
            invoice           = invoice,
            room              = invoice.room,
            notification_type = "auto_disconnect",
            message           = AUTO_DISCONNECT_TEXT,
        )
        logger.info(
            "[NotificationService] auto_disconnect sent — invoice_id=%s room=%s",
            invoice.id, invoice.room,
        )

        # إرسال SMS/WhatsApp للطلاب النشطين في الغرفة
        active_students = Student.objects.filter(room=invoice.room, status='active')
        sms_success_count = 0
        sms_attempted = False

        for student in active_students:
            if student.phone:
                sms_attempted = True
                try:
                    success = NotificationChannelService.send_sms(student.phone, AUTO_DISCONNECT_TEXT)
                    if success:
                        sms_success_count += 1
                except Exception as exc:
                    logger.error(
                        "[NotificationService] تعذر إرسال رسالة SMS/واتساب، سيبقى الإشعار الداخلي فعالاً: %s", exc
                    )

        if sms_attempted:
            if sms_success_count > 0:
                notification.sms_status = 'sent'
            else:
                notification.sms_status = 'failed'
                logger.error("[NotificationService] تعذر إرسال رسالة SMS/واتساب لجميع الطلاب، سيبقى الإشعار الداخلي فعالاً")
            notification.save(update_fields=['sms_status'])

        return notification
