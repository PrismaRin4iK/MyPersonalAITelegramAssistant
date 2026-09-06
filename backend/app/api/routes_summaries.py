from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.database import get_db
from backend.app.summaries.service import SummaryService
from backend.app.telegram.service import telegram_service
from backend.app.telegram.simulator import simulator_gateway

router = APIRouter(tags=["summaries"])

class RunSummaryRequest(BaseModel):
    title: Optional[str] = "Telegram Digest"
    hours_back: Optional[int] = 24

@router.post("/summaries/run")
async def run_summary(req: Optional[RunSummaryRequest] = None, db: AsyncSession = Depends(get_db)):
    title = req.title if req else "Telegram Digest"
    hours = req.hours_back if req else 24
    digest_text = await SummaryService.generate_periodic_digest(db, digest_title=title, hours_back=hours)
    return {"success": True, "digest": digest_text}

@router.get("/saved-messages")
async def get_saved_messages():
    # Return simulated or stored Saved Messages
    return simulator_gateway.saved_messages
