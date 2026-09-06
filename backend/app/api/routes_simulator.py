from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.telegram.simulator import simulator_gateway
from backend.app.security.circuit_breaker import circuit_breaker

router = APIRouter(prefix="/simulator", tags=["simulator"])

class SendSimulatedMessage(BaseModel):
    chat_id: str
    sender_id: str
    sender_name: str
    text: str
    chat_title: Optional[str] = None
    chat_type: Optional[str] = "private"

@router.get("/chats")
async def get_simulator_chats():
    return await simulator_gateway.fetch_dialogs()

@router.post("/send")
async def send_simulated_message(req: SendSimulatedMessage):
    result = await simulator_gateway.simulate_incoming(
        chat_id=req.chat_id,
        sender_id=req.sender_id,
        sender_name=req.sender_name,
        text=req.text,
        chat_title=req.chat_title,
        chat_type=req.chat_type or "private",
    )
    return {"success": True, "message": result}

@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker():
    circuit_breaker.reset()
    return {"success": True, "status": "Circuit breaker reset to NORMAL"}
