from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.database import get_db
from backend.app.actions.approval_queue import ApprovalQueue

router = APIRouter(prefix="/actions", tags=["actions"])

class ApproveRequest(BaseModel):
    edited_text: Optional[str] = None

class RejectRequest(BaseModel):
    reason: Optional[str] = "Rejected by user"

@router.get("")
@router.get("/pending")
async def list_pending_actions(db: AsyncSession = Depends(get_db)):
    return await ApprovalQueue.get_pending_drafts(db)

@router.post("/{action_id}/approve")
async def approve_action(action_id: int, req: Optional[ApproveRequest] = None, db: AsyncSession = Depends(get_db)):
    edited = req.edited_text if req else None
    res = await ApprovalQueue.approve_and_send(db, action_id, edited_text=edited)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.post("/{action_id}/reject")
async def reject_action(action_id: int, req: Optional[RejectRequest] = None, db: AsyncSession = Depends(get_db)):
    reason = req.reason if req else "Rejected by user"
    res = await ApprovalQueue.reject_draft(db, action_id, reason=reason)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res
