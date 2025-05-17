import random
import requests
from django.core.cache import cache
import urllib.parse
import pytz
from datetime import datetime
from django.conf import settings

def send_sms(payload):
    mobile_number = payload.get("mobile_number")
    message = payload.get("message")
    
    print(mobile_number, message, "--------------------------------")

    if not mobile_number or not message:
        return {"error": "Mobile number and message are required"}

    # URL encode the message
    encoded_message = requests.utils.quote(message)
    print(f"Encoded message: {encoded_message}")

    # Replace this with your actual API URL
    sms_api_url = f"https://7l7dy2zq63.execute-api.ap-south-1.amazonaws.com/default/smsapi/?option=publishMessage&passKey=IamJiseniorJi@374&phoneNumber={mobile_number}&customMessage={encoded_message}"

    try:
        response = requests.get(sms_api_url)
        print(f"API Response: {response.text}")
        if response.status_code == 200:
            return {"message": "SMS sent successfully"}
        else:
            return {"error": "Failed to send SMS:{response.text}"}
    except Exception as e:
        print(f"Exception: {str(e)}")
        return {"error": str(e)}
    
    

# AUTH_SERVICE_MOBILE_URL =  settings.AUTH_SERVER_URL + "/member-details/",

def get_member_details_by_mobile(mobile_number):
    try:
        response = requests.get(settings.AUTH_SERVER_URL + "/member-details/", params={"mobile_number": mobile_number})
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException as e:
        print(f"Error contacting auth service: {e}")
        return None
    
    


# AUTH_SERVICE_CARD_URL = settings.AUTH_SERVER_URL + "/cardno/member-details/",  

def get_member_details_by_card(card_number):
    try:
        response = requests.get(settings.AUTH_SERVER_URL + "/cardno/member-details/", params={"card_number": card_number})
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException as e:
        print(f"Error contacting auth service: {e}")
        return None
    
    
    
    
    
# AUTH_SERVICE_BUSINESS_URL = settings.AUTH_SERVER_URL + "/business/details/",

def get_business_details_by_id(business_id):
    try:
        response = requests.get(settings.AUTH_SERVER_URL + "/business/details/", params={"business_id": business_id})
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException as e:
        print(f"Error contacting auth service: {e}")
        return None


