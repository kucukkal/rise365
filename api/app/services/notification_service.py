import firebase_admin
from firebase_admin import credentials, messaging
from app.config import settings
import os

_initialized = False

def init_firebase():
    global _initialized
    if _initialized:
        return
    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    if not cred_path or not os.path.exists(cred_path):
        print("⚠️  Firebase credentials not found — notifications disabled")
        return
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _initialized = True
        print("✅ Firebase initialized")
    except Exception as e:
        print(f"❌ Firebase init error: {e}")

def send_notification(token: str, title: str, body: str, data: dict = None) -> bool:
    if not _initialized:
        print(f"[DEV] Notification skipped (no Firebase): {title} — {body}")
        return True
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default", badge=1)
                )
            ),
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(sound="default")
            )
        )
        messaging.send(message)
        return True
    except Exception as e:
        print(f"Notification error: {e}")
        return False

def send_multicast(tokens: list, title: str, body: str, data: dict = None) -> int:
    if not tokens:
        return 0
    if not _initialized:
        print(f"[DEV] Multicast skipped ({len(tokens)} tokens): {title}")
        return len(tokens)
    try:
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            tokens=tokens,
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default", badge=1)
                )
            ),
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(sound="default")
            )
        )
        response = messaging.send_each_for_multicast(message)
        return response.success_count
    except Exception as e:
        print(f"Multicast error: {e}")
        return 0

init_firebase()
