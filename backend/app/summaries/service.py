import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.app.db.models import Analysis, Message, Chat, TaskItem
from backend.app.telegram.service import telegram_service
from backend.app.security.crypto import decrypt_text

class SummaryService:
    """
    Builds and formats instant notifications and periodic digests
    delivered to 'Saved Messages' (Избранное) (Section 7).
    """

    @classmethod
    async def send_instant_summary(
        cls,
        sender_name: str,
        chat_title: str,
        analysis: Analysis,
        raw_text: str,
    ) -> Dict[str, Any]:
        """Dispatches an immediate alert to Saved Messages for high importance messages."""
        urgency_emoji = "🚨" if (analysis.importance >= 8 or analysis.urgency >= 8) else "📌"
        actions_block = ""
        if analysis.action_items:
            actions_block = "\n⚡️ Действия:\n" + "\n".join(f"  • {item}" for item in analysis.action_items)

        topics_str = ", ".join(analysis.topics) if analysis.topics else "Общее"
        text = (
            f"{urgency_emoji} Важное сообщение ({analysis.importance}/10)\n"
            f"👤 От: {sender_name} ({chat_title})\n"
            f"📝 Суть: {analysis.summary}\n"
            f"🏷 Темы: {topics_str}"
            f"{actions_block}"
        )

        gateway = telegram_service.active_gateway
        return await gateway.send_to_saved_messages(text)

    @classmethod
    async def generate_periodic_digest(
        cls,
        session: AsyncSession,
        digest_title: str = "Telegram Digest",
        hours_back: int = 12,
    ) -> str:
        """
        Builds periodic digest (hourly, morning, or evening) from recent analyses and open tasks.
        Format follows Section 7.2 specification.
        """
        since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_back)

        # 1. Fetch recent analyses
        q = (
            select(Analysis, Message)
            .join(Message, Analysis.message_id == Message.id)
            .where(Analysis.created_at >= since)
            .order_by(desc(Analysis.importance))
        )
        res = await session.execute(q)
        rows = res.all()

        urgent_items = []
        work_items = []
        other_count = 0

        for analysis, message in rows:
            sender = message.sender_name or f"User {message.sender_id}"
            first_clause = analysis.summary or "Новое сообщение"
            if analysis.importance >= 8 or analysis.urgency >= 8:
                urgent_items.append(f"• {first_clause}")
            elif analysis.importance >= 5:
                work_items.append(f"• {first_clause}")
            else:
                other_count += 1

        # 2. Fetch open tasks
        task_q = select(TaskItem).where(TaskItem.status == "open").limit(5)
        task_res = await session.execute(task_q)
        open_tasks = task_res.scalars().all()

        # Format output
        now_time = datetime.datetime.utcnow().strftime("%H:%M")
        lines = [f"📋 {digest_title} — {now_time} UTC\n"]

        if urgent_items:
            lines.append("🚨 Срочно:")
            lines.extend(urgent_items)
            lines.append("")

        if work_items:
            lines.append("💼 Важные темы:")
            lines.extend(work_items)
            lines.append("")

        if other_count > 0:
            lines.append(f"ℹ️ Остальное: {other_count} сообщений без срочных действий.\n")

        if open_tasks:
            lines.append("📌 Открытые задачи:")
            for t in open_tasks:
                lines.append(f"  ▫️ {t.title}")
            lines.append("")

        if len(lines) == 1:
            lines.append("За прошедший период новых критических событий не зафиксировано.")

        digest_text = "\n".join(lines).strip()

        # Deliver to Saved Messages
        gateway = telegram_service.active_gateway
        await gateway.send_to_saved_messages(digest_text)
        return digest_text
