import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from backend.app.db.database import init_db, AsyncSessionLocal
from backend.app.db.models import Chat, Contact, Message, Analysis, ActionItem
from backend.workers.pipeline import message_pipeline
from backend.app.telegram.telethon_client import telethon_gateway

@pytest.mark.asyncio
async def test_end_to_end_pipeline():
    from backend.app.config import settings
    orig_key = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = ""
    try:
        await init_db()
        message_pipeline.start()

        # Mock telethon saved messages dispatch
        mock_saved = []
        async def fake_send_to_saved(text):
            entry = {"text": text}
            mock_saved.append(entry)
            return entry

        telethon_gateway.send_to_saved_messages = fake_send_to_saved

        test_text = "Привет! У нас упал прод из-за ошибки в токене JWT! Срочно посмотри!"
        payload = {
            "telegram_message_id": "test_msg_999",
            "chat_id": "chat_test_123",
            "chat_title": "Группа Разработка",
            "chat_type": "private",
            "sender_id": "user_test_999",
            "sender_name": "Иван Тест",
            "direction": "incoming",
            "text": test_text,
            "timestamp": "2026-09-04T00:00:00",
        }
        await message_pipeline.enqueue_event(payload)

        # Wait briefly for worker queue processing
        await asyncio.sleep(1.0)

        # Verify message and analysis in DB
        async with AsyncSessionLocal() as session:
            msg_res = await session.execute(
                select(Message).where(Message.sender_id == "user_test_999").order_by(Message.id.desc()).limit(1)
            )
            msg = msg_res.scalars().first()
            assert msg is not None

            an_res = await session.execute(
                select(Analysis).where(Analysis.message_id == msg.id)
            )
            analysis = an_res.scalar_one_or_none()
            assert analysis is not None
            assert analysis.importance >= 8

        # Verify instant summary was dispatched
        assert len(mock_saved) > 0
        saved_text = mock_saved[0]["text"]
        assert "Telegram Alert" in saved_text or "Иван Тест" in saved_text

    finally:
        await message_pipeline.stop()
        settings.GEMINI_API_KEY = orig_key
