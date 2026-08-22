import os
import random
import string
import redis
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
    # Dev mode — no real SendGrid key
    if not settings.SENDGRID_API_KEY or settings.SENDGRID_API_KEY.startswith("your_"):
        return code == "123456"
    key = f"admin_otp:{email}"
    stored = _redis.get(key)
    if not stored:
        return False
    if stored.decode() == code:
        _redis.delete(key)
        return True
    return False

def send_otp_email(email: str, otp: str) -> bool:
    # Dev mode — print to terminal
    if not settings.SENDGRID_API_KEY:
        print(f"📧 [DEV] OTP for {email}: {otp}")
        return True

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        message = Mail(
            from_email=os.getenv("SENDGRID_FROM_EMAIL", "kucukkalmu@gmail.com"),
            to_emails=email,
            subject="Rise365 Admin — Your OTP Code",
            html_content=f"""
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
        )
        sg.send(message)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False
