import os
from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    DATA_DIR: Path = DATA_DIR
    # App info
    APP_NAME: str = "Telegram AI Assistant"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Security & Encryption
    SECRET_KEY: str = "super-secret-jwt-key-please-change-in-production-32bytesmin"
    ENCRYPTION_KEY: str = "w-6bK8_eS3b0wHk3_Yk83h21kLm9P_qWxYzAbCdEfGh="  # 32-byte urlsafe base64 for Fernet
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DATA_DIR}/assistant.db"
    
    # Telegram MTProto Credentials
    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""
    TELEGRAM_PHONE: str = ""
    TELEGRAM_SESSION_NAME: str = "tg_personal_session"
    USE_SIMULATOR_BY_DEFAULT: bool = False
    
    # AI Provider configuration
    AI_PROVIDER: str = "gemini"  # auto, openai, gemini, ollama, heuristic
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    GEMINI_PROXY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    AI_MODEL: str = "default"
    
    # Response Guard & Limits
    RATE_LIMIT_PER_MINUTE_CHAT: int = 5
    RATE_LIMIT_PER_MINUTE_GLOBAL: int = 20
    CIRCUIT_BREAKER_ERROR_THRESHOLD: int = 5
    CIRCUIT_BREAKER_WINDOW_SECONDS: int = 60
    MAX_REPLY_LENGTH: int = 800
    
    # Data Retention (TTL in days)
    RAW_MESSAGE_TTL_DAYS: int = 7
    SUMMARY_TTL_DAYS: int = 30
    
    model_config = ConfigDict(env_file=".env", extra="allow")

import json

def load_ai_config_override(cfg: Settings):
    ai_file = DATA_DIR / "ai_config.json"
    if ai_file.exists():
        try:
            with open(ai_file, "r") as f:
                data = json.load(f)
            if data.get("gemini_api_key"):
                cfg.GEMINI_API_KEY = data["gemini_api_key"]
            if data.get("gemini_model"):
                cfg.GEMINI_MODEL = data["gemini_model"]
            if data.get("provider"):
                cfg.AI_PROVIDER = data["provider"]
            if "gemini_proxy" in data:
                cfg.GEMINI_PROXY = data.get("gemini_proxy", "")
        except Exception:
            pass

settings = Settings()
load_ai_config_override(settings)
