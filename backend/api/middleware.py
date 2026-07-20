"""
api/middleware.py
مكافئ notFound.js — Middleware يرجع 404 موحد لأي URL غير موجود
يُسجَّل في settings.py تحت MIDDLEWARE
"""
import json
from django.http import JsonResponse
from django.urls import resolve, Resolver404


class NotFoundMiddleware:
    """
    مكافئ notFound.js في Express:
    يعترض أي طلب لـ URL غير مسجّل في urlpatterns
    ويرجع: { success: false, message: "المسار غير موجود" }
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # حاول resolve المسار أولاً
        try:
            resolve(request.path)
            # إذا نجح → طلب عادي، أكمل السلسلة
            return self.get_response(request)
        except Resolver404:
            # المسار غير موجود → 404 موحد
            return JsonResponse(
                {
                    'success': False,
                    'status': 'fail',
                    'message': 'المسار غير موجود',
                    'path': request.path,
                },
                status=404,
                json_dumps_params={'ensure_ascii': False},
            )
