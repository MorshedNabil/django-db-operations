from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.exceptions import InvalidToken
from .database import UserDB # Make sure you import your database

class RawSQLJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken("Token is missing user ID claim")

        user = UserDB.get_user_by_id(user_id)
        if user is None:
            raise AuthenticationFailed("User not found", code="user_not_found")

        class AuthenticatedUserMock:
            def __init__(self, data):
                self.id = data['user_id']
                self.username = data['name']
                self.email = data['email']
                self.is_authenticated = True
                self.data = data
        return AuthenticatedUserMock(user)