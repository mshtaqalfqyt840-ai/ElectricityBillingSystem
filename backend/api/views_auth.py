from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from .models import User
from .serializers import LoginSerializer

class LoginView(APIView):
    authentication_classes = [] # لا نطلب توكن للدخول لهذه الصفحة
    permission_classes = []     # مسموح للجميع

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            try:
                user = User.objects.get(username=username)
                # نتحقق من تطابق كلمة المرور (سواء كانت نص عادي أو مشفرة)
                if password == user.password_hash or check_password(password, user.password_hash):
                    refresh = RefreshToken.for_user(user)
                    return Response({
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'role': user.role
                        }
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({'error': 'كلمة المرور غير صحيحة'}, status=status.HTTP_401_UNAUTHORIZED)
            except User.DoesNotExist:
                return Response({'error': 'المستخدم غير موجود'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
