from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import requests
from django.conf import settings


class SSOMemberTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return None

        token = auth_header.split("Token ")[1]

        try:
            response = requests.post(
                settings.AUTH_SERVER_URL + "/api/member/verify-token/",
                json={"token": token},
                timeout=5
            )
            if response.status_code != 200:
                raise AuthenticationFailed("Invalid or expired token.")

            data = response.json()
            user = AuthenticatedMemberUser(
                id=data["user_id"],
                mbrcardno=data["mbrcardno"],
                full_name=data["full_name"]
            )
            print(user,"==============")
            return (user, None)
        except requests.RequestException:
            raise AuthenticationFailed("Authentication service unreachable.")



class AuthenticatedMemberUser:
    def __init__(self, id, mbrcardno, full_name):
        self.id = id
        self.mbrcardno = mbrcardno  # store mbrcardno
        self.full_name = full_name
        self.is_authenticated = True

    def __str__(self):
        return f"MemberUser {self.mbrcardno}"
