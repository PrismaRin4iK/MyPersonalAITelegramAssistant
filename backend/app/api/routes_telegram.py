from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.app.telegram.service import telegram_service
from backend.app.telegram.telethon_client import telethon_gateway
from backend.app.security.circuit_breaker import circuit_breaker

router = APIRouter(prefix="/telegram", tags=["telegram"])

class ConnectRequest(BaseModel):
    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    phone: Optional[str] = None
    mode: Optional[str] = "simulator"  # "simulator" or "telethon"

class PhoneCodeRequest(BaseModel):
    phone: str
    api_id: int
    api_hash: str

class CompleteLoginRequest(BaseModel):
    code: Optional[str] = None
    password_2fa: Optional[str] = None

class SwitchModeRequest(BaseModel):
    mode: str  # "simulator" or "telethon"

@router.get("/status")
async def get_telegram_status():
    status = await telegram_service.get_status()
    cb_tripped, cb_reason, cb_time = circuit_breaker.get_trip_info()
    status["circuit_breaker"] = {
        "is_tripped": cb_tripped,
        "reason": cb_reason,
        "tripped_at": cb_time,
    }
    return status

@router.post("/connect")
async def connect_telegram(req: ConnectRequest):
    if req.mode == "telethon":
        telegram_service.switch_mode("telethon")
        res = await telethon_gateway.connect(api_id=req.api_id, api_hash=req.api_hash)
        return res
    else:
        telegram_service.switch_mode("simulator")
        res = await telegram_service.active_gateway.connect()
        return res

@router.post("/disconnect")
async def disconnect_telegram():
    active = telegram_service.active_gateway
    return await active.disconnect()

class QrCodeRequest(BaseModel):
    api_id: int
    api_hash: str

@router.post("/request-qr")
async def request_qr_login(req: QrCodeRequest):
    return await telethon_gateway.request_qr_login(req.api_id, req.api_hash)

@router.post("/check-qr")
async def check_qr_login():
    res = await telethon_gateway.check_qr_login()
    if res.get("success") and res.get("authorized"):
        telegram_service.switch_mode("telethon")
    return res

@router.post("/request-code")
async def request_phone_code(req: PhoneCodeRequest):
    return await telethon_gateway.request_phone_code(req.phone, req.api_id, req.api_hash)

@router.post("/complete-login")
async def complete_login(req: CompleteLoginRequest):
    res = await telethon_gateway.complete_phone_login(req.code, req.password_2fa)
    if res.get("success") and res.get("authorized"):
        telegram_service.switch_mode("telethon")
    return res

@router.post("/switch-mode")
async def switch_mode(req: SwitchModeRequest):
    telegram_service.switch_mode(req.mode)
    return await telegram_service.get_status()

@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker():
    from backend.app.security.circuit_breaker import circuit_breaker
    circuit_breaker.reset()
    return await telegram_service.get_status()
