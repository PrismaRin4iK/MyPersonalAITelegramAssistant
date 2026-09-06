from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.app.db.database import get_db
from backend.app.db.models import Contact
from backend.app.categories.service import CategoriesService

router = APIRouter(prefix="/categories", tags=["categories"])

class CategoryCreateRequest(BaseModel):
    id: str
    name: str
    color: Optional[str] = "#38bdf8"
    icon: Optional[str] = "Tag"
    description: Optional[str] = ""
    prompt_instruction: Optional[str] = ""

@router.get("")
async def list_categories(db: AsyncSession = Depends(get_db)):
    categories = CategoriesService.get_categories()
    
    # Calculate contact count per category
    counts_res = await db.execute(
        select(Contact.category, func.count(Contact.id)).group_by(Contact.category)
    )
    counts = dict(counts_res.all())

    result = []
    for cat in categories:
        item = dict(cat)
        item["contact_count"] = counts.get(cat["id"], 0)
        result.append(item)

    return result

@router.post("")
async def create_or_update_category(req: CategoryCreateRequest):
    if not req.id or not req.name:
        raise HTTPException(status_code=400, detail="ID и название категории обязательны")
    
    cat = CategoriesService.save_category(
        cat_id=req.id,
        name=req.name,
        color=req.color or "#38bdf8",
        icon=req.icon or "Tag",
        description=req.description or "",
        prompt_instruction=req.prompt_instruction or "",
    )
    return cat

@router.delete("/{category_id}")
async def delete_category(category_id: str):
    success = CategoriesService.delete_category(category_id)
    if not success:
        raise HTTPException(status_code=400, detail="Невозможно удалить стандартную категорию или категория не найдена")
    return {"success": True, "message": f"Категория {category_id} удалена"}
