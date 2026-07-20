"""
api/services/notification_channel_service.py
طبقة الخدمات (Service Layer) — مكوّن خدمة قنوات الإشعارات (SMS/WhatsApp).

يفصل هذا الملف منطق إرسال الرسائل عن الـ Services الأخرى، ويُتيح استبدال طبقة الاتصال الفعلية (Adapter) بسهولة لاحقاً.
"""
import logging
import time

logger = logging.getLogger(__name__)

# إعدادات آلية إعادة المحاولة
MAX_RETRIES = 2
RETRY_DELAY_S = 0.5

def _send_sms_command(phone_number: str, message: str) -> bool:
    """
    -- MOCK --
    يحاكي إرسال رسالة SMS/WhatsApp. يرجع True دائماً الآن لمحاكاة النجاح.
    في الإنتاج: يستبدل بطلب HTTP لمزود خدمة حقيقي (Twilio / WhatsApp API).
    """
    logger.debug(
        "[NotificationChannelAdapter:Mock] phone=%s message='%s' -> simulated success",
        phone_number, message,
    )
    # TODO: استبدل هذا الكتلة باستدعاء الشبكة الفعلي عند تحديد بروتوكول المزود
    return True

class NotificationChannelService:
    """
    خدمة قنوات الإشعارات (SMS/WhatsApp).

    الاستخدام:
        NotificationChannelService.send_sms(phone_number="05xxxxxxxx", message="...")
    """

    @classmethod
    def send_sms(cls, phone_number: str, message: str) -> bool:
        """ينفذ أمر الإرسال بآلية retry ويرجع True عند النجاح أو False عند الفشل النهائي."""
        logger.info("[NotificationChannelService] send_sms requested for phone=%s", phone_number)
        
        attempt = 0
        last_error = None

        while attempt <= MAX_RETRIES:
            attempt += 1
            try:
                success = _send_sms_command(phone_number, message)
                if success:
                    logger.info("[NotificationChannelService] SUCCESS — phone=%s", phone_number)
                    return True
                raise RuntimeError(f"_send_sms_command returned False for phone={phone_number}")
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "[NotificationChannelService] send_sms attempt %d/%d failed — phone=%s: %s",
                    attempt, MAX_RETRIES + 1, phone_number, exc,
                )
                if attempt <= MAX_RETRIES:
                    time.sleep(RETRY_DELAY_S)
        
        logger.error(
            "[NotificationChannelService] FINAL FAILURE — phone=%s after %d attempts. Error: %s",
            phone_number, attempt, last_error,
        )
        return False
