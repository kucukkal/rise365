import os
import random
import string
import redis
import urllib.request
import urllib.error
import json
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

    # Dev mode
    if not resend_key:
        print(f"📧 [DEV] Admin OTP: {otp}")
        return True

    try:
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
              If you didn't request this, ignore this email.
            </p>
          </div>
        </div>
        """

        payload = json.dumps({
            "from": "Rise365 <onboarding@resend.dev>",
            "to": [email],
            "subject": "Rise365 Admin — Your OTP Code",
            "html": html,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {resend_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            print(f"✅ OTP email sent via Resend: {result}")
            return True

    except Exception as e:
        print(f"❌ Email error: {e}")
        return False
