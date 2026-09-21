from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Protected MongoDB vars (keep as required by environment)
    MONGO_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "test_database"

    # MySQL - Primary Database
    ASYNC_DATABASE_URL: str = "mysql+aiomysql://root@localhost/catering_saas"
    SYNC_DATABASE_URL: str = "mysql+pymysql://root@localhost/catering_saas"

    # JWT
    JWT_SECRET: str = "change-this-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # TOTP (Fernet key for encrypting TOTP secrets)
    TOTP_ENCRYPTION_KEY: str = ""

    # App
    APP_NAME: str = "Catering SaaS"
    DEBUG: bool = False
    COOKIE_SECURE: bool = False

    # Storage
    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_PATH: str = "/app/storage"

    # Super Admin (seeded on startup)
    SUPER_ADMIN_EMAIL: str = "admin@example.com"
    SUPER_ADMIN_PASSWORD: str = "changeme"

    # CORS - handled programmatically in server.py
    CORS_ORIGINS: str = "*"

    model_config = {"env_file": ".env", "extra": "allow"}


settings = Settings()
