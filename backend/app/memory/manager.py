import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from backend.app.db.models import Contact, ConversationMemory, TaskItem, Message, Analysis, ActionItem, AuditLog
from backend.app.config import settings

class MemoryManager:
    """
    Manages long-term contact memory, tasks, TTL pruning, and privacy data deletion (Sections 6, 16).
    """

    @classmethod
    async def record_contact_facts(
        cls,
        session: AsyncSession,
        contact_id: int,
        source_message_id: int,
        topics: List[str],
        action_items: List[str],
    ):
        """Extracts and persists pertinent facts and open tasks for a contact."""
        now = datetime.datetime.utcnow()
        ttl_days = settings.SUMMARY_TTL_DAYS
        expires_at = now + datetime.timedelta(days=ttl_days)

        # 1. Store topic facts
        if topics:
            fact_str = f"Обсуждаемые темы: {', '.join(topics)}"
            mem = ConversationMemory(
                contact_id=contact_id,
                fact=fact_str,
                source_message_id=source_message_id,
                expires_at=expires_at,
            )
            session.add(mem)

        # 2. Store open action tasks
        for item in action_items:
            task = TaskItem(
                source_message_id=source_message_id,
                contact_id=contact_id,
                title=item,
                status="open",
            )
            session.add(task)

    @classmethod
    async def get_contact_context(
        cls,
        session: AsyncSession,
        contact_id: int,
    ) -> tuple[List[str], List[str]]:
        """Retrieves active facts and unclosed tasks for a contact."""
        mem_q = select(ConversationMemory).where(ConversationMemory.contact_id == contact_id).limit(5)
        mem_res = await session.execute(mem_q)
        facts = [m.fact for m in mem_res.scalars().all()]

        task_q = select(TaskItem).where(TaskItem.contact_id == contact_id, TaskItem.status == "open").limit(5)
        task_res = await session.execute(task_q)
        tasks = [t.title for t in task_res.scalars().all()]

        return facts, tasks

    @classmethod
    async def prune_expired_data(cls, session: AsyncSession) -> dict:
        """Prunes expired raw messages according to TTL."""
        now = datetime.datetime.utcnow()
        cutoff = now - datetime.timedelta(days=settings.RAW_MESSAGE_TTL_DAYS)

        res = await session.execute(delete(Message).where(Message.created_at < cutoff))
        deleted_count = res.rowcount
        await session.commit()
        return {"pruned_messages": deleted_count}

    @classmethod
    async def wipe_all_data(cls, session: AsyncSession) -> dict:
        """
        Complete Privacy Data Erasure (Sections 6.2, 16).
        Wipes all messages, analyses, memory facts, tasks, and actions.
        """
        await session.execute(delete(ActionItem))
        await session.execute(delete(Analysis))
        await session.execute(delete(ConversationMemory))
        await session.execute(delete(TaskItem))
        await session.execute(delete(Message))
        await session.execute(delete(AuditLog))
        await session.commit()
        return {"status": "success", "message": "All messages, analyses, memory, and tasks wiped successfully"}
