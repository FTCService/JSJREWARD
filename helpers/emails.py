import requests
import urllib.parse

def send_cupon_email(email, subject, html_body):
    """
    Send an email using the external BulkEmail API.
    """
    api_url = "https://w1yg18jn76.execute-api.ap-south-1.amazonaws.com/default/sesapi"

    # # Ensure the recipient email is clean
    # if email.endswith(".com.com"):
    #     email = email.replace(".com.com", ".com")

    # URL encode subject and body
    encoded_subject = urllib.parse.quote(subject)
    encoded_body = urllib.parse.quote(html_body)

    try: 
        # Construct the full URL with query parameters
        full_url = f"{api_url}?sender=avinash.singh.270504@gmail.com&recipient={email}&subject={encoded_subject}&body={encoded_body}"

        response = requests.get(full_url)

        # Debug print
        print("Requested URL:", full_url)

        # Check response status
        if response.status_code == 200:
            print(f"✅ Email sent to: {email}")
            return True
        else:
            print(f"❌ Failed to send to {email}. Status: {response.status_code}")
            print(f"Response Content: {response.content.decode()}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending to {email}: {e}")
        return False
