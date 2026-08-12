from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_VERIFY_SERVICE_SID: str = ""

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = ""

    # App
    APP_NAME: str = "Rise365"
    ADMIN_EMAIL: str = "kucukkalmu@gmail.com"
    SENDGRID_API_KEY: str = ""
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "Rise365Admin!"
    DEBUG: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
