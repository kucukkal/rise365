"""Push notifications for Circles. Silently skipped when Firebase isn't configured
(e.g. on your Mac), so features keep working without it."""
import os, json, base64


def _firebase_ready() -> bool:
    try:
        import firebase_admin
        from firebase_admin import credentials
        if firebase_admin._apps:
            return True
        raw = os.getenv("FIREBASE_CREDENTIALS_BASE64")
        if not raw:
            return False
        info = json.loads(base64.b64decode(raw))
        firebase_admin.initialize_app(credentials.Certificate(info))
        return True
    except Exception as e:
        print(f"push: firebase unavailable ({e})")
        return False


def send_push(user, title: str, body: str, data: dict | None = None) -> None:
    token = getattr(user, "fcm_token", None)
    if not token or not _firebase_ready():
        print(f"push (not sent): {title} — {body}")
        return
    try:
        from firebase_admin import messaging
        messaging.send(messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
        ))
    except Exception as e:
        print(f"push error: {e}")
