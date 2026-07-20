from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        """
        يُشغَّل مرة واحدة عند اكتمال تحميل Django.
        يُسجّل مهمة send_critical_warnings لتعمل كل ساعة عبر APScheduler.

        os.environ guard: يمنع تشغيل الـ Scheduler مرتين في وضع StatReloader
        (Django يُشغّل عمليتين: watchdog + main).
        """
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            return  # عملية الـ watchdog — نتجاهلها

        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval    import IntervalTrigger
        from django_apscheduler.jobstores     import DjangoJobStore

        from .tasks import send_critical_warnings, auto_disconnect_overdue_invoices

        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), 'default')

        scheduler.add_job(
            send_critical_warnings,
            trigger    = IntervalTrigger(hours=1),
            id         = 'send_critical_warnings',
            name       = 'إرسال إنذارات حرجة لمهلة السداد',
            replace_existing = True,
            max_instances    = 1,      # لا تتداخل المهمة مع نفسها
            misfire_grace_time = 300,  # 5 دقائق سماحية قبل اعتبار المهمة فائتة
        )

        scheduler.add_job(
            auto_disconnect_overdue_invoices,
            trigger    = IntervalTrigger(hours=1),
            id         = 'auto_disconnect_overdue_invoices',
            name       = 'فصل آلي للعداد لانتهاء مهلة السداد',
            replace_existing = True,
            max_instances    = 1,
            misfire_grace_time = 300,
        )

        from .tasks import check_overdue_installments
        scheduler.add_job(
            check_overdue_installments,
            trigger    = IntervalTrigger(hours=24),
            id         = 'check_overdue_installments',
            name       = 'فحص تأخر خطط التقسيط',
            replace_existing = True,
            max_instances    = 1,
            misfire_grace_time = 300,
        )

        scheduler.start()
