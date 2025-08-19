from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import requests
from django.conf import settings
from django.contrib.auth.models import AnonymousUser

class SSOBusinessTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return None

        token = auth_header.split("Token ")[1]

        try:
            response = requests.post(
                settings.AUTH_SERVER_URL + "/api/verify-token/",
                json={"token": token},
                timeout=5
            )
            if response.status_code != 200:
                raise AuthenticationFailed("Invalid or expired token.")

            data = response.json()
            user = AuthenticatedBusinessUser(
                id=data["user_id"],
                business_id=data["business_id"],
                business_name=data["business_name"]
            )

            return (user, None)
        except requests.RequestException:
            raise AuthenticationFailed("Authentication service unreachable.")
        
        
        

class AuthenticatedBusinessUser:
    def __init__(self, id, business_id, business_name):
        self.id = id
        self.business_id = business_id
        self.business_name = business_name
        self.is_authenticated = True  # Required by DRF

    def __str__(self):
        return f"BusinessUser {self.business_id}"
    
    
    
    
