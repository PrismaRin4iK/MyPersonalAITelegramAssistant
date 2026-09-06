from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.database import get_db
from backend.app.db.models import AiProfile

router = APIRouter(prefix="/ai-profiles", tags=["ai-profiles"])

class ProfileCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_policy: str
    style: str = "friendly"
    max_tokens: int = 200
    forbidden_topics: List[str] = []
    allowed_actions: List[str] = ["draft", "summary"]
    is_default: bool = False

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_policy: Optional[str] = None
    style: Optional[str] = None
    max_tokens: Optional[int] = None
    forbidden_topics: Optional[List[str]] = None
    allowed_actions: Optional[List[str]] = None
    is_default: Optional[bool] = None

@router.get("")
async def list_profiles(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AiProfile).order_by(AiProfile.id.asc()))
    profiles = res.scalars().all()
    return profiles

@router.post("")
async def create_profile(profile_in: ProfileCreate, db: AsyncSession = Depends(get_db)):
    profile = AiProfile(
        name=profile_in.name,
        description=profile_in.description,
        system_policy=profile_in.system_policy,
        style=profile_in.style,
        max_tokens=profile_in.max_tokens,
        forbidden_topics=profile_in.forbidden_topics,
        allowed_actions=profile_in.allowed_actions,
        is_default=profile_in.is_default,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile

@router.patch("/{profile_id}")
async def update_profile(profile_id: int, update: ProfileUpdate, db: AsyncSession = Depends(get_db)):
    profile = await db.get(AiProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="AI Profile not found")

    if update.name is not None:
        profile.name = update.name
    if update.description is not None:
        profile.description = update.description
    if update.system_policy is not None:
        profile.system_policy = update.system_policy
    if update.style is not None:
        profile.style = update.style
    if update.max_tokens is not None:
        profile.max_tokens = update.max_tokens
    if update.forbidden_topics is not None:
        profile.forbidden_topics = update.forbidden_topics
    if update.allowed_actions is not None:
        profile.allowed_actions = update.allowed_actions
    if update.is_default is not None:
        profile.is_default = update.is_default

    await db.commit()
    await db.refresh(profile)
    return profile
