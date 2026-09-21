import hashlib
import secrets
import base64
from io import BytesIO
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt
import pyotp
import qrcode
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError
from cryptography.fernet import Fernet
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# ─── Password Hashing (Argon2id) ──────────────────────────────────────────────
# argon2-cffi >= 21.2 defaults to Argon2id (Type.ID)
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


def needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


# ─── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(
    user_id: int,
    email: str,
    is_super_admin: bool = False,
    tenant_id: Optional[int] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "is_super_admin": is_super_admin,
        "tenant_id": tenant_id,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int, session_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "sid": session_id,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_mfa_pending_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "mfa_pending",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# ─── TOTP ─────────────────────────────────────────────────────────────────────

def _get_fernet() -> Fernet:
    key = settings.TOTP_ENCRYPTION_KEY
    if not key:
        # Fallback for dev — derive from JWT_SECRET
        raw = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
        key = base64.urlsafe_b64encode(raw).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def encrypt_totp_secret(secret: str) -> str:
    return _get_fernet().encrypt(secret.encode()).decode()


def decrypt_totp_secret(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


def get_totp_qr_base64(secret: str, email: str, issuer: Optional[str] = None) -> str:
    issuer_name = issuer or settings.APP_NAME
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(email, issuer_name=issuer_name)

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{encoded}"


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


# ─── Recovery Codes ───────────────────────────────────────────────────────────

def generate_recovery_codes(count: int = 8) -> tuple[list[str], list[str]]:
    """Returns (plaintext_codes, sha256_hashed_codes)."""
    plaintext, hashed = [], []
    for _ in range(count):
        raw = secrets.token_hex(8).upper()
        code = f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"
        plaintext.append(code)
        hashed.append(hash_recovery_code(code))
    return plaintext, hashed


def hash_recovery_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()


def verify_recovery_code(code: str, hashed: str) -> bool:
    return hash_recovery_code(code) == hashed


# ─── Generic Token Hashing ────────────────────────────────────────────────────

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ─── Rate Limiter ─────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)
