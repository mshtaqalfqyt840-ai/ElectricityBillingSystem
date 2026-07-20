import os
import logging
from .audit_service import AuditLogger

logger = logging.getLogger(__name__)

class PaymentGatewayService:
    """
    خدمة تجريدية للربط مع بوابات الدفع الإلكتروني (مثل Moyasar).
    """

    @classmethod
    def verify_transaction(cls, transaction_id, wallet_provider, amount, user=None):
        """
        التحقق من صحة معاملة مالية آلياً عبر بوابة الدفع.
        
        تعيد إحدى الحالات التالية:
        - 'verified': التحقق ناجح والمبلغ مطابق.
        - 'failed': التحقق فشل (رقم خاطئ، مبلغ غير مطابق، مرفوضة).
        - 'unavailable': الخدمة غير متاحة (أخطاء اتصال، بوابة غير مهيأة).
        """
        # تجهيز رقم الحوالة الآمن (إخفاء كل الأرقام عدا آخر 4)
        safe_transaction_id = f"****{transaction_id[-4:]}" if transaction_id and len(transaction_id) > 4 else "****"
        
        try:
            # TODO: دمج مكتبة Moyasar هنا (Moyasar.Payment.fetch(transaction_id)) 
            # واستخدام مفتاح الربط (API Key) من المتغيرات البيئية.
            
            # محاكاة الرد من خلال متغير بيئة للاختبار
            mock_mode = os.environ.get('PAYMENT_GATEWAY_MOCK_MODE', 'unavailable').lower()
            
            if mock_mode not in ['verified', 'failed', 'unavailable']:
                mock_mode = 'unavailable'
            
            result = mock_mode
            
            # تسجيل المحاولة في الـ Audit Log
            AuditLogger.log(
                actor=user,
                action_type='payment_gateway_verification',
                target_model='Transaction',
                target_id=safe_transaction_id,
                description=f"محاكاة للتحقق من المعاملة عبر بوابة الدفع: النتيجة {result}",
                metadata={
                    'provider': wallet_provider,
                    'amount_requested': str(amount),
                    'result': result,
                    'gateway': 'Moyasar (Mock)'
                }
            )
            
            return result

        except Exception as e:
            logger.error(f"خطأ في الاتصال ببوابة الدفع للمعاملة {safe_transaction_id}: {str(e)}")
            
            # في حال الانقطاع أو الخطأ البرمجي، نسجل الخطأ ونرجع 'unavailable' بمسار آمن
            AuditLogger.log(
                actor=user,
                action_type='payment_gateway_verification_error',
                target_model='Transaction',
                target_id=safe_transaction_id,
                description="خطأ أثناء محاولة الاتصال ببوابة الدفع",
                metadata={
                    'provider': wallet_provider,
                    'error': str(e),
                    'gateway': 'Moyasar (Mock)'
                }
            )
            return 'unavailable'
