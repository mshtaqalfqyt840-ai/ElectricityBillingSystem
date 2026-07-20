import logging

logger = logging.getLogger(__name__)

class AuditLogger:
    @staticmethod
    def log(actor, action_type, target_model, target_id, description, metadata=None):
        """
        يسجل إجراءً مهماً في سجل التدقيق (AuditLog).
        مُغلف بـ try/except لتجنب تعطيل العملية الأساسية في حال الفشل.
        """
        try:
            from api.models import AuditLog
            AuditLog.objects.create(
                actor=actor,
                action_type=action_type,
                target_model=target_model,
                target_id=str(target_id),
                description=description,
                metadata=metadata or {}
            )
        except Exception as e:
            logger.error(
                f"[AuditLogger] Failed to log action: {action_type} for {target_model}({target_id}). Error: {str(e)}"
            )
