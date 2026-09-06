from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.app.db.database import get_db
from backend.app.db.models import Message, Analysis, AuditLog, TaskItem, Chat
from backend.app.security.crypto import decrypt_text
from backend.app.memory.manager import MemoryManager

router = APIRouter(tags=["messages_and_audit"])

@router.get("/messages")
async def list_messages(
    chat_id: Optional[int] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Message, Chat).join(Chat, Message.chat_id == Chat.id)
    if chat_id:
        q = q.where(Message.chat_id == chat_id)
    q = q.order_by(desc(Message.id)).limit(limit)

    res = await db.execute(q)
    rows = res.all()

    items = []
    for msg, chat in rows:
        items.append({
            "id": msg.id,
            "chat_id": chat.telegram_chat_id,
            "chat_title": chat.title,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender_name,
            "direction": msg.direction,
            "text": decrypt_text(msg.encrypted_content),
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        })
    return items

@router.get("/analyses")
async def list_analyses(limit: int = Query(50, le=200), db: AsyncSession = Depends(get_db)):
    q = (
        select(Analysis, Message)
        .join(Message, Analysis.message_id == Message.id)
        .order_by(desc(Analysis.id))
        .limit(limit)
    )
    res = await db.execute(q)
    rows = res.all()

    items = []
    for a, m in rows:
        items.append({
            "id": a.id,
            "message_id": m.id,
            "sender_name": m.sender_name,
            "intent": a.intent,
            "importance": a.importance,
            "urgency": a.urgency,
            "needs_reply": a.needs_reply,
            "summary": a.summary,
            "topics": a.topics,
            "action_items": a.action_items,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return items

@router.get("/tasks")
async def list_tasks(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(TaskItem)
    if status:
        q = q.where(TaskItem.status == status)
    q = q.order_by(desc(TaskItem.id))
    res = await db.execute(q)
    return res.scalars().all()

@router.post("/tasks/{task_id}/toggle")
async def toggle_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(TaskItem, task_id)
    if task:
        task.status = "done" if task.status == "open" else "open"
        await db.commit()
        await db.refresh(task)
        return task
    return {"error": "Task not found"}

@router.get("/audit-logs")
async def list_audit_logs(limit: int = Query(50, le=200), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AuditLog).order_by(desc(AuditLog.id)).limit(limit))
    return res.scalars().all()

@router.post("/privacy/wipe")
async def wipe_data(db: AsyncSession = Depends(get_db)):
    return await MemoryManager.wipe_all_data(db)
