import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.app.db.models import ActionItem, Message, Chat, AuditLog
from backend.app.security.guard import ResponseGuard
from backend.app.security.circuit_breaker import circuit_breaker
from backend.app.telegram.service import telegram_service

class ApprovalQueue:
    """
    Manages drafts requiring manual approval (Stage 2: черновики)
    and executes user-approved transmissions safely.
    """

    @classmethod
    async def get_pending_drafts(cls, session: AsyncSession) -> List[Dict[str, Any]]:
        q = (
            select(ActionItem, Message, Chat)
            .join(Message, ActionItem.message_id == Message.id)
            .join(Chat, Message.chat_id == Chat.id)
            .where(ActionItem.status == "pending")
            .order_by(desc(ActionItem.created_at))
        )
        res = await session.execute(q)
        drafts = []
        for action, msg, chat in res.all():
            drafts.append({
                "id": action.id,
                "message_id": msg.id,
                "chat_id": chat.telegram_chat_id,
                "chat_title": chat.title,
                "sender_id": msg.sender_id,
                "sender_name": msg.sender_name,
                "incoming_text": msg.metadata_json.get("preview_text", ""),
                "proposed_text": action.proposed_text,
                "reason": action.reason,
                "created_at": action.created_at.isoformat() if action.created_at else None,
            })
        return drafts

    @classmethod
    async def approve_and_send(
        cls,
        session: AsyncSession,
        action_id: int,
        edited_text: Optional[str] = None,
        actor: str = "user",
    ) -> Dict[str, Any]:
        action = await session.get(ActionItem, action_id)
        if not action:
            return {"success": False, "error": "Action item not found"}

        if action.status != "pending":
            return {"success": False, "error": f"Action is already {action.status}"}

        msg = await session.get(Message, action.message_id)
        chat = await session.get(Chat, msg.chat_id)

        final_text = (edited_text or action.proposed_text or "").strip()

        # Perform final Response Guard check before transmission (Section 14)
        guard = ResponseGuard.validate(
            text=final_text,
            chat_enabled=chat.enabled,
            auto_reply_enabled=True,  # User explicitly approved this specific transmission
        )
        if not guard.is_allowed:
            action.status = "blocked"
            action.result = f"Guard blocked approval: {guard.reason}"
            await session.commit()
            return {"success": False, "error": guard.reason}

        # Send via active Telegram gateway
        gateway = telegram_service.active_gateway
        try:
            send_res = await gateway.send_message(
                chat_id=chat.telegram_chat_id,
                text=guard.sanitized_text,
                reply_to_msg_id=msg.telegram_message_id,
            )

            circuit_breaker.record_reply_sent(chat.telegram_chat_id)

            action.status = "executed"
            action.decision = "approved"
            action.result = f"Sent successfully (id: {send_res.get('message_id')})"

            audit = AuditLog(
                actor=actor,
                event_type="draft_approved_and_sent",
                object=f"chat:{chat.telegram_chat_id}",
                metadata_json={
                    "action_id": action.id,
                    "final_text": final_text[:100],
                    "sent_message_id": send_res.get("message_id"),
                },
            )
            session.add(audit)
            await session.commit()

            return {"success": True, "action_id": action.id, "sent_message": send_res}

        except Exception as e:
            action.result = f"Send error: {str(e)}"
            circuit_breaker.record_error(str(e))
            await session.commit()
            return {"success": False, "error": str(e)}

    @classmethod
    async def reject_draft(
        cls,
        session: AsyncSession,
        action_id: int,
        reason: str = "Rejected by user",
        actor: str = "user",
    ) -> Dict[str, Any]:
        action = await session.get(ActionItem, action_id)
        if not action:
            return {"success": False, "error": "Action item not found"}

        action.status = "rejected"
        action.decision = "rejected"
        action.result = reason

        audit = AuditLog(
            actor=actor,
            event_type="draft_rejected",
            object=f"action:{action.id}",
            metadata_json={"reason": reason},
        )
        session.add(audit)
        await session.commit()
        return {"success": True, "action_id": action.id, "status": "rejected"}
