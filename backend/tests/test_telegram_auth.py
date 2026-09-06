import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.app.telegram.telethon_client import TelethonGateway

@pytest.mark.asyncio
async def test_request_phone_code_normalization_and_error_handling():
    gateway = TelethonGateway()

    # Mock TelegramClient
    with patch("backend.app.telegram.telethon_client.TelegramClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_sent = MagicMock()
        mock_sent.phone_code_hash = "mock_hash_123"
        mock_sent.timeout = 120
        mock_client.send_code_request = AsyncMock(return_value=mock_sent)
        mock_client_cls.return_value = mock_client

        # Test phone number starting with 8 (RU local format)
        res = await gateway.request_phone_code("8 (999) 123-45-67", 12345, "mock_hash")
        assert res["success"] is True
        assert res["phone"] == "+79991234567"
        assert res["phone_code_hash"] == "mock_hash_123"

        # Verify send_code_request was called with clean normalized phone
        mock_client.send_code_request.assert_called_once_with("+79991234567")

@pytest.mark.asyncio
async def test_request_phone_code_exception_handling():
    gateway = TelethonGateway()

    with patch("backend.app.telegram.telethon_client.TelegramClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.send_code_request = AsyncMock(side_effect=RuntimeError("SendCodeUnavailableError: code unavailable"))
        mock_client_cls.return_value = mock_client

        res = await gateway.request_phone_code("+79991234567", 999, "bad_hash")
        assert res["success"] is False
        assert "SendCodeUnavailable" in res["error"] or "временно ограничил" in res["error"]

