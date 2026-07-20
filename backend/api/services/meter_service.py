"""
api/services/meter_service.py
طبقة الخدمات (Service Layer) — مكوّن خدمة التحكم في العدادات الذكية.

يفصل هذا الملف منطق إرسال الأوامر عن الـ Views تماماً، ويُتيح استبدال طبقة الاتصال الفعلية (Adapter) بسهولة لاحقاً.
"""
import logging
import time
from django.utils import timezone

from ..models import Meter
from ..exceptions import MeterCommandError

logger = logging.getLogger(__name__)

# إعدادات آلية إعادة المحاولة
MAX_RETRIES = 2
RETRY_DELAY_S = 0.5

def _send_meter_command(meter_serial: str, command: str) -> bool:
    """
    -- MOCK --
    يحاكي إرسال أمر للعداد عبر الشبكة. يرجع True دائماً الآن لمحاكاة النجاح.
    في الإنتاج: يستبدل بطلب HTTP / MQTT / Socket حقيقي للعداد الذكي.
    """
    logger.debug(
        "[MeterAdapter:Mock] serial=%s command=%s -> simulated success",
        meter_serial, command,
    )
    # TODO: استبدل هذا الكتلة باستدعاء الشبكة الفعلي عند تحديد بروتوكول المزود
    return True

class MeterCommandService:
    """
    خدمة التحكم في العدادات الذكية.

    الاستخدام:
        MeterCommandService.connect(room_id=5)
        MeterCommandService.disconnect(room_id=5)
    """

    @classmethod
    def _execute(cls, room_id: int, command: str) -> None:
        """ينفذ الأمر المطلوب بآلية retry ثم يحدّث قاعدة البيانات."""
        
        # 1. جلب سجل العداد
        try:
            meter = Meter.objects.select_related('room').get(room_id=room_id)
        except Meter.DoesNotExist:
            logger.warning(
                "[MeterCommandService] room_id=%s has no Meter record — skipping command '%s'",
                room_id, command,
            )
            return

        new_status = 'connected' if command == 'connect' else 'disconnected'
        action_ar = 'التوصيل' if command == 'connect' else 'الفصل'
        attempt = 0
        last_error = None

        # 2. آلية إعادة المحاولة
        while attempt <= MAX_RETRIES:
            attempt += 1
            try:
                success = _send_meter_command(meter.meter_serial, command)
                if success:
                    break
                raise RuntimeError(
                    f"_send_meter_command returned False for serial={meter.meter_serial}"
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "[MeterCommandService] %s attempt %d/%d failed — room_id=%s serial=%s: %s",
                    command, attempt, MAX_RETRIES + 1, room_id, meter.meter_serial, exc,
                )
                if attempt <= MAX_RETRIES:
                    time.sleep(RETRY_DELAY_S)
        else:
            # 3. استنفاد جميع المحاولات -> فشل نهائي
            logger.error(
                "[MeterCommandService] FINAL FAILURE — command=%s room_id=%s serial=%s after %d attempts. Error: %s",
                command, room_id, meter.meter_serial, attempt, last_error,
            )
            
            # تحديث قاعدة البيانات بحالة الفشل
            meter.last_command_sent_at = timezone.now()
            meter.last_command_status = f"failed after {attempt} attempts: {last_error}"
            meter.save(update_fields=['last_command_sent_at', 'last_command_status'])

            raise MeterCommandError(
                command=command,
                room_id=room_id,
                attempts=attempt,
            )

        # 4. نجاح -> تحديث قاعدة البيانات
        meter.connection_status = new_status
        meter.last_command_sent_at = timezone.now()
        meter.last_command_status = f"success: {action_ar} by system"
        meter.save(update_fields=['connection_status', 'last_command_sent_at', 'last_command_status'])

        logger.info(
            "[MeterCommandService] SUCCESS — command=%s room_id=%s serial=%s -> status=%s",
            command, room_id, meter.meter_serial, new_status,
        )

    @classmethod
    def connect(cls, room_id: int) -> None:
        """إرسال أمر التوصيل للعداد الذكي للغرفة المحددة."""
        logger.info("[MeterCommandService] connect requested for room_id=%s", room_id)
        cls._execute(room_id, 'connect')

    @classmethod
    def disconnect(cls, room_id: int) -> None:
        """إرسال أمر الفصل للعداد الذكي للغرفة المحددة."""
        logger.info("[MeterCommandService] disconnect requested for room_id=%s", room_id)
        cls._execute(room_id, 'disconnect')
