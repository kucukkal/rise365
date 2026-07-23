from twilio.rest import Client
from app.config import settings

def get_twilio_client():
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def send_otp(phone: str) -> bool:
    try:
        client = get_twilio_client()
        verification = client.verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verifications.create(to=phone, channel="sms")
        return verification.status == "pending"
    except Exception as e:
        print(f"Twilio error: {e}")
        return False

def verify_otp(phone: str, code: str) -> bool:
    try:
        client = get_twilio_client()
        result = client.verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verification_checks.create(to=phone, code=code)
        return result.status == "approved"
    except Exception as e:
        print(f"Twilio verify error: {e}")
        return False
