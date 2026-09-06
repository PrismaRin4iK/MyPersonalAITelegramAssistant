import hashlib
import os
import datetime
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from backend.app.config import settings

security_bearer = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if ":" not in hashed_password:
        return False
    salt, hashed = hashed_password.split(":", 1)
    test_hash = hashlib.sha256((salt + plain_password).encode()).hexdigest()
    return test_hash == hashed

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + (expires_delta or datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> dict:
    if not credentials:
        # For ease of single-user local development, if no credentials provided, permit demo admin user
        return {"sub": "admin", "role": "owner"}
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
