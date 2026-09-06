from typing import Dict, Any, Optional
from backend.app.config import settings
from backend.app.telegram.gateway import TelegramGateway
from backend.app.telegram.telethon_client import telethon_gateway

class TelegramService:
    def __init__(self):
        self.mode = "telethon"
        self._custom_gateway: Optional[TelegramGateway] = None

    @property
    def active_gateway(self) -> TelegramGateway:
        return self._custom_gateway or telethon_gateway

    @active_gateway.setter
    def active_gateway(self, gw: Optional[TelegramGateway]):
        self._custom_gateway = gw

    def switch_mode(self, mode: str):
        self.mode = "telethon"

    async def get_status(self) -> Dict[str, Any]:
        active = self.active_gateway
        status = await active.get_status()
        status["active_mode"] = self.mode
        return status

telegram_service = TelegramService()
