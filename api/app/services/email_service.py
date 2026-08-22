import os
import random
import string
import redis
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
    gmail_user = os.getenv("GMAIL_USER", "")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD", "")

    # Dev mode — print to terminal if no Gmail configured
    if not gmail_user or not gmail_password:
        print(f"📧 [DEV] Admin OTP: {otp}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Rise365 Admin — Your OTP Code"
        msg["From"] = f"Rise365 <{gmail_user}>"
        msg["To"] = email

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

        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, email, msg.as_string())

        print(f"✅ OTP email sent to {email}")
        return True

    except Exception as e:
        print(f"❌ Email error: {e}")
        return False
