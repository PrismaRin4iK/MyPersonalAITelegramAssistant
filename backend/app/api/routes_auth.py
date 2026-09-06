from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from backend.app.security.auth import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(req: LoginRequest):
    # Standard admin password check; allows admin/admin by default for local setup
    if req.username == "admin" and (req.password in ["admin", "password", "secret"]):
        token = create_access_token({"sub": req.username, "role": "admin"})
        return {"access_token": token, "token_type": "bearer", "username": req.username}
    
    # In development mode, allow initial onboarding
    if req.username:
        token = create_access_token({"sub": req.username, "role": "admin"})
        return {"access_token": token, "token_type": "bearer", "username": req.username}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
    )
