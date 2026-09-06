import pytest
from backend.app.ai.analyzer import AIAnalyzer, AnalysisResult

from backend.app.config import settings

@pytest.fixture(autouse=True)
def reset_gemini_key():
    orig = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = ""
    yield
    settings.GEMINI_API_KEY = orig

@pytest.mark.asyncio
async def test_analyzer_task_extraction():
    text = "Привет! Есть проблема с авторизацией JWT после обновления токена, сможешь глянуть завтра?"
    res = await AIAnalyzer.analyze(text, "Иван Петров", "Разработка")

    assert isinstance(res, AnalysisResult)
    assert res.intent == "task"
    assert res.importance >= 7
    assert res.urgency >= 6
    assert res.needs_reply is True
    assert "JWT" in res.topics
    assert any("JWT" in item or "токен" in item for item in res.action_items)

@pytest.mark.asyncio
async def test_analyzer_spam_detection():
    text = "Заработок от 5000$ в день! Пассивный доход, переходи по bit.ly/easy-money"
    res = await AIAnalyzer.analyze(text, "Crypto Spammer", "PM")

    assert res.intent == "spam"
    assert res.importance == 1
    assert res.needs_reply is False

@pytest.mark.asyncio
async def test_analyzer_question():
    text = "Когда ожидать новый билд для тестирования?"
    res = await AIAnalyzer.analyze(text, "Тестировщик", "QA")

    assert res.intent in ["question", "task"]
    assert res.needs_reply is True

@pytest.mark.asyncio
async def test_gemini_analysis_mocked():
    from unittest.mock import patch, AsyncMock, MagicMock
    from backend.app.config import settings

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '{"intent": "urgent", "importance": 9, "urgency": 9, "needs_reply": true, "summary": "Срочная проблема с базой", "topics": ["db", "crash"], "action_items": ["перезапустить"]}'
                        }
                    ]
                }
            }
        ]
    }

    settings.GEMINI_API_KEY = "test_fake_gemini_key"
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await AIAnalyzer.analyze("Срочно упала база!", "Админ", "DevOps")
        assert res.intent == "urgent"
        assert res.importance == 9
        assert res.urgency == 9
        assert res.needs_reply is True
        assert "db" in res.topics
        assert "перезапустить" in res.action_items
    settings.GEMINI_API_KEY = ""
