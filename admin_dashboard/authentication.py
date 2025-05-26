from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import requests
from django.conf import settings
from django.contrib.auth.models import AnonymousUser

class SSOUserTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return None

        token = auth_header.split("Token ")[1]

        try:
            response = requests.post(
                settings.AUTH_SERVER_URL + "/verify-token/",
                json={"token": token},
                timeout=5
            )
            if response.status_code != 200:
                raise AuthenticationFailed("Invalid or expired token.")

            data = response.json()
            user = AuthenticatedBusinessUser(
                id=data["id"],
                employee_id=data["employee_id"],
                business_name=data["full_name"],
                email=data["email"]
            )

            return (user, None)
        except requests.RequestException:
            raise AuthenticationFailed("Authentication service unreachable.")
        
        
        

class AuthenticatedBusinessUser:
    def __init__(self, id, employee_id, full_name, email):
        self.id = id
        self.employee_id = employee_id
        self.full_name = full_name
        self.email = email
        self.is_authenticated = True  # Required by DRF

    def __str__(self):
        return f"BusinessUser {self.employee_id}"
    
    
    
    
