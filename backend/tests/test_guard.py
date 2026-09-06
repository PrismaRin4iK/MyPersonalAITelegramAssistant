import pytest
from backend.app.security.guard import ResponseGuard

def test_guard_allows_safe_text():
    res = ResponseGuard.validate(
        text="Привет, Иван! Понял задачу, завтра с утра всё проверю.",
        chat_enabled=True,
        auto_reply_enabled=True,
    )
    assert res.is_allowed is True
    assert "завтра" in res.sanitized_text

def test_guard_blocks_bot_commands():
    res = ResponseGuard.validate(
        text="/start welcome to the platform",
        chat_enabled=True,
        auto_reply_enabled=True,
    )
    assert res.is_allowed is False
    assert "prohibited command" in res.reason

def test_guard_blocks_shell_commands():
    res = ResponseGuard.validate(
        text="rm -rf /tmp/data",
        chat_enabled=True,
        auto_reply_enabled=True,
    )
    assert res.is_allowed is False

def test_guard_blocks_api_key_leaks():
    res = ResponseGuard.validate(
        text="Вот ключ доступа: sk-abc123456789012345678901234567890",
        chat_enabled=True,
        auto_reply_enabled=True,
    )
    assert res.is_allowed is False
    assert "sensitive credential pattern detected" in res.reason

def test_guard_blocks_when_auto_reply_disabled():
    res = ResponseGuard.validate(
        text="Обычный ответ",
        chat_enabled=True,
        auto_reply_enabled=False,
        is_whitelisted=False,
    )
    assert res.is_allowed is False
    assert "Auto-reply is not enabled" in res.reason

def test_guard_enforces_length_limit():
    long_text = "слово " * 300
    res = ResponseGuard.validate(
        text=long_text,
        chat_enabled=True,
        auto_reply_enabled=True,
        max_length=50,
    )
    assert res.is_allowed is False
    assert "exceeds maximum permissible limit" in res.reason
