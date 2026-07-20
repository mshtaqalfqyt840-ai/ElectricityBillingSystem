from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from .models import User

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        """
        Returns a custom user model instance based on the token's payload.
        """
        try:
            user_id = validated_token.get('user_id')
            if not user_id:
                raise AuthenticationFailed('Token contained no recognizable user identification', code='token_not_valid')

            user = User.objects.get(id=user_id)
            return user
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found', code='user_not_found')
