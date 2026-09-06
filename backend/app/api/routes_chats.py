from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.database import get_db
from backend.app.db.models import Chat

router = APIRouter(prefix="/chats", tags=["chats"])

class ChatUpdate(BaseModel):
    title: Optional[str] = None
    enabled: Optional[bool] = None
    auto_reply_enabled: Optional[bool] = None
    summary_enabled: Optional[bool] = None

@router.get("")
async def list_chats(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Chat).order_by(Chat.id.desc()))
    chats = res.scalars().all()
    return chats

@router.patch("/{chat_id}")
async def update_chat(chat_id: int, update: ChatUpdate, db: AsyncSession = Depends(get_db)):
    chat = await db.get(Chat, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    if update.title is not None:
        chat.title = update.title
    if update.enabled is not None:
        chat.enabled = update.enabled
    if update.auto_reply_enabled is not None:
        chat.auto_reply_enabled = update.auto_reply_enabled
    if update.summary_enabled is not None:
        chat.summary_enabled = update.summary_enabled

    await db.commit()
    await db.refresh(chat)
    return chat
