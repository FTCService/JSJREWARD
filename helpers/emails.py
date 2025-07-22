import threading
import requests
from django.template.loader import render_to_string
from django.conf import settings


def send_template_email(subject, template_name, context, recipient_list, attachments=None):
    """
    Send an email by invoking your AWS Lambda SES API.
    Supports HTML content and optional attachments.
    """
    # Render the HTML content
    html_message = render_to_string(template_name, context)

    sender = "contact@jsjcard.com"  # Your verified SES sender email
    recipient = recipient_list[0] if recipient_list else None

    if not recipient:
        print("No recipient provided.")
        return

    api_url = "https://w1yg18jn76.execute-api.ap-south-1.amazonaws.com/default/sesapi"

    # Prepare payload
    payload = {
        "sender": sender,
        "recipient": recipient,
        "subject": subject,
        "body": html_message
    }

    # If attachments are provided, encode them as JSON string
    if attachments:
        payload["attachments"] = attachments  # Must be a list of dicts as per your Lambda spec

    headers = {"Content-Type": "application/json"}

    def send_email():
        try:
            response = requests.post(api_url, json=payload, headers=headers)
            if response.status_code == 200:
                print("✅ Email sent successfully via AWS SES API.")
            else:
                print(f"❌ Failed to send email. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            print(f"❌ Exception while sending email: {e}")

    threading.Thread(target=send_email).start()
