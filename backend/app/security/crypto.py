import base64
import re
from cryptography.fernet import Fernet
from backend.app.config import settings

# Ensure encryption key is valid 32-byte Fernet key
def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY.encode()
    # If key is not valid fernet format, derive one cleanly
    if len(key) != 44:
        import hashlib
        derived = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
        return Fernet(derived)
    return Fernet(key)

_fernet = _get_fernet()

def encrypt_text(plain_text: str) -> str:
    """Encrypts plain text at rest using Fernet (AES-128-CBC + HMAC)."""
    if not plain_text:
        return ""
    return _fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")

def decrypt_text(cipher_text: str) -> str:
    """Decrypts cipher text at rest."""
    if not cipher_text:
        return ""
    try:
        return _fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception:
        return "[Decryption failed: corrupted or modified ciphertext]"

# Redaction patterns for logs (Section 8.4)
SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(password|passwd|pwd|pass)[:=]\s*(\S+)", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key|secret|token|auth_token)[:=]\s*(\S+)", re.IGNORECASE),
    re.compile(r"1[0-9]{8,10}:[a-zA-Z0-9_-]{35}"),  # Telegram Bot Token
    re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),  # JWT
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----"),
]

def redact_sensitive_data(text: str) -> str:
    """Sanitizes text by redacting passwords, tokens, and secrets."""
    if not text:
        return ""
    result = text
    for pattern in SENSITIVE_PATTERNS:
        result = pattern.sub(r"\1: [REDACTED]", result)
    return result

def anonymize_id(entity_id: str | int) -> str:
    """Pseudonymizes chat_id or user_id for safe logging (e.g. tg_123***89)."""
    s = str(entity_id)
    if len(s) <= 4:
        return "****"
    return f"{s[:3]}***{s[-2:]}"
