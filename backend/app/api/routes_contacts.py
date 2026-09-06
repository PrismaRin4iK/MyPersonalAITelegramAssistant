from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.app.db.database import get_db
from backend.app.db.models import Contact, ConversationMemory, TaskItem, Message, ActionItem
from backend.app.telegram.telethon_client import telethon_gateway

router = APIRouter(prefix="/contacts", tags=["contacts"])

class ContactUpdate(BaseModel):
    category: Optional[str] = None
    ai_mode: Optional[str] = None  # analysis_only, draft, auto_reply, ignored
    profile_id: Optional[int] = None
    is_whitelisted: Optional[bool] = None
    is_blacklisted: Optional[bool] = None
    notes: Optional[str] = None

@router.get("")
async def list_contacts(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Contact).order_by(Contact.id.desc()))
    contacts = res.scalars().all()
    return contacts

@router.post("/sync")
async def sync_contacts(db: AsyncSession = Depends(get_db)):
    if not telethon_gateway.is_connected:
        raise HTTPException(
            status_code=400, 
            detail="Telegram аккаунт не подключен. Сначала авторизуйтесь во вкладке 'Настройки & MTProto'."
        )

    tg_contacts = await telethon_gateway.fetch_contacts()
    if not tg_contacts:
        return {
            "success": True, 
            "count": 0, 
            "added": 0, 
            "updated": 0, 
            "message": "В Telegram не найдено контактов или список пуст"
        }

    # Existing contacts in DB
    existing_res = await db.execute(select(Contact))
    existing_contacts = {c.telegram_user_id: c for c in existing_res.scalars().all()}

    added_count = 0
    updated_count = 0

    for c_data in tg_contacts:
        uid = c_data["telegram_user_id"]
        if uid in existing_contacts:
            contact = existing_contacts[uid]
            changed = False
            if c_data["display_name"] and contact.display_name != c_data["display_name"]:
                contact.display_name = c_data["display_name"]
                changed = True
            if c_data["username"] and contact.username != c_data["username"]:
                contact.username = c_data["username"]
                changed = True
            if c_data["phone"] and contact.phone != c_data["phone"]:
                contact.phone = c_data["phone"]
                changed = True
            if changed:
                updated_count += 1
        else:
            cat = "friend" if c_data.get("is_contact") else "stranger"
            new_contact = Contact(
                telegram_user_id=uid,
                display_name=c_data["display_name"],
                username=c_data["username"],
                phone=c_data["phone"],
                category=cat,
                ai_mode="analysis_only",
                is_whitelisted=False,
                is_blacklisted=False,
            )
            db.add(new_contact)
            added_count += 1

    await db.commit()

    return {
        "success": True,
        "total_fetched": len(tg_contacts),
        "added": added_count,
        "updated": updated_count,
        "message": f"Успешно подтянуто {len(tg_contacts)} контактов из Telegram (новых: {added_count}, обновлено: {updated_count})"
    }

@router.get("/{contact_id}/details")
async def get_contact_details(contact_id: int, db: AsyncSession = Depends(get_db)):
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Fetch memories
    mem_res = await db.execute(
        select(ConversationMemory).where(ConversationMemory.contact_id == contact_id).order_by(desc(ConversationMemory.id))
    )
    memories = mem_res.scalars().all()

    # Fetch tasks
    task_res = await db.execute(
        select(TaskItem).where(TaskItem.contact_id == contact_id).order_by(desc(TaskItem.id))
    )
    tasks = task_res.scalars().all()

    # Fetch recent actions
    act_res = await db.execute(
        select(ActionItem, Message)
        .join(Message, ActionItem.message_id == Message.id)
        .where(Message.sender_id == contact.telegram_user_id)
        .order_by(desc(ActionItem.id))
        .limit(10)
    )
    action_rows = act_res.all()
    actions = [
        {
            "id": a.id,
            "action_type": a.action_type,
            "decision": a.decision,
            "reason": a.reason,
            "status": a.status,
            "result": a.result,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a, m in action_rows
    ]

    return {
        "contact": contact,
        "memories": memories,
        "tasks": tasks,
        "recent_actions": actions,
    }

@router.patch("/{contact_id}")
async def update_contact(contact_id: int, update: ContactUpdate, db: AsyncSession = Depends(get_db)):
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    if update.category is not None:
        contact.category = update.category
    if update.ai_mode is not None:
        contact.ai_mode = update.ai_mode
    if update.profile_id is not None:
        contact.profile_id = update.profile_id
    if update.is_whitelisted is not None:
        contact.is_whitelisted = update.is_whitelisted
    if update.is_blacklisted is not None:
        contact.is_blacklisted = update.is_blacklisted
    if update.notes is not None:
        contact.notes = update.notes

    await db.commit()
    await db.refresh(contact)
    return contact
