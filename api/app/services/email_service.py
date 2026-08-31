import os
import random
import string
import redis
from app.config import settings

# Redis for OTP storage
_redis = redis.from_url(settings.REDIS_URL)
OTP_EXPIRY = 600  # 10 minutes

def generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))

def store_otp(email: str, otp: str):
    key = f"admin_otp:{email}"
    _redis.setex(key, OTP_EXPIRY, otp)

def verify_email_otp(email: str, code: str) -> bool:
    key = f"admin_otp:{email}"
    stored = _redis.get(key)
    if not stored:
        return False
    if stored.decode() == code:
        _redis.delete(key)
        return True
    return False

def send_otp_email(email: str, otp: str) -> bool:
    resend_key = os.getenv("RESEND_API_KEY", "")
    print(f"Resend key prefix: {resend_key[:10] if resend_key else 'EMPTY'}")

    if not resend_key:
        print(f"Admin OTP: {otp}")
        return True

    try:
        import resend
        resend.api_key = resend_key

        html = f"""
        <div style="font-family:sans-serif;max-width:400px;margin:0 auto;padding:20px">
          <div style="background:#1D9E75;border-radius:12px;padding:24px;text-align:center">
            <h2 style="color:white;margin:0">Rise365 Admin</h2>
          </div>
          <div style="padding:24px;background:#f8f9fa;border-radius:12px;margin-top:12px">
            <p style="color:#333;font-size:15px">Your admin verification code:</p>
            <div style="background:white;border-radius:8px;padding:20px;text-align:center;
                 font-size:36px;font-weight:bold;letter-spacing:12px;color:#1D9E75;
                 border:2px solid #1D9E75;margin:16px 0">
              {otp}
            </div>
            <p style="color:#666;font-size:13px">
              This code expires in 10 minutes.<br>
              If you did not request this, ignore this email.
            </p>
          </div>
        </div>
        """

        params = {
            "from": "Rise365 <noreply@rise365app.com>",
            "to": [email],
            "subject": "Rise365 Admin — Your OTP Code",
            "html": html,
        }

        email_response = resend.Emails.send(params)
        print(f"✅ OTP email sent: {email_response}")
        return True

    except Exception as e:
        print(f"❌ Email error: {e}")
        # Fall back — show OTP in logs
        print(f"Admin OTP: {otp}")
        return False
