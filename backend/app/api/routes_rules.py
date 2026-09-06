from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.database import get_db
from backend.app.db.models import Rule

router = APIRouter(prefix="/rules", tags=["rules"])

class RuleCreate(BaseModel):
    name: str
    scope: str  # global, user, group, chat_type, category
    subject: Optional[str] = None
    action: str  # allow_auto, force_draft, ignore, analysis_only, ban
    priority: int = 100
    conditions: Dict[str, Any] = {}
    is_active: bool = True

class RuleUpdate(BaseModel):
    name: Optional[str] = None
    scope: Optional[str] = None
    subject: Optional[str] = None
    action: Optional[str] = None
    priority: Optional[int] = None
    conditions: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

@router.get("")
async def list_rules(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Rule).order_by(Rule.priority.asc()))
    rules = res.scalars().all()
    return rules

@router.post("")
async def create_rule(rule_in: RuleCreate, db: AsyncSession = Depends(get_db)):
    new_rule = Rule(
        name=rule_in.name,
        scope=rule_in.scope,
        subject=rule_in.subject,
        action=rule_in.action,
        priority=rule_in.priority,
        conditions=rule_in.conditions,
        is_active=rule_in.is_active,
    )
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    return new_rule

@router.patch("/{rule_id}")
async def update_rule(rule_id: int, update: RuleUpdate, db: AsyncSession = Depends(get_db)):
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if update.name is not None:
        rule.name = update.name
    if update.scope is not None:
        rule.scope = update.scope
    if update.subject is not None:
        rule.subject = update.subject
    if update.action is not None:
        rule.action = update.action
    if update.priority is not None:
        rule.priority = update.priority
    if update.conditions is not None:
        rule.conditions = update.conditions
    if update.is_active is not None:
        rule.is_active = update.is_active

    await db.commit()
    await db.refresh(rule)
    return rule

@router.delete("/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(rule)
    await db.commit()
    return {"success": True, "deleted_id": rule_id}
