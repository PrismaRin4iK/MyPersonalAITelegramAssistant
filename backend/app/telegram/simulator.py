import uuid
import datetime
from typing import Callable, Coroutine, Any, Optional, List, Dict
from backend.app.telegram.gateway import TelegramGateway

class SimulatorGateway(TelegramGateway):
    """
    High-fidelity Telegram Sandbox & Simulator.
    Allows full end-to-end operation without real Telegram API credentials.
    """

    def __init__(self):
        self.is_connected: bool = True
        self.account_info: Dict[str, Any] = {
            "telegram_user_id": "tg_user_1001",
            "username": "alex_engineer",
            "first_name": "Alex",
            "phone": "+79991234567",
            "is_simulator": True,
            "connected_at": datetime.datetime.utcnow().isoformat(),
        }
        self._listener: Optional[Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]] = None
        
        # Saved messages ("Избранное") virtual storage
        self.saved_messages: List[Dict[str, Any]] = []

        # Simulated chats and their message histories
        self.simulated_chats: Dict[str, Dict[str, Any]] = {
            "chat_ivan": {
                "chat_id": "chat_ivan",
                "title": "Иван Петров (Разработка)",
                "type": "private",
                "sender_id": "user_ivan",
                "sender_name": "Иван Петров",
                "messages": [],
            },
            "chat_maria": {
                "chat_id": "chat_maria",
                "title": "Мария Смирнова (Дизайн)",
                "type": "private",
                "sender_id": "user_maria",
                "sender_name": "Мария Смирнова",
                "messages": [],
            },
            "chat_client": {
                "chat_id": "chat_client",
                "title": "Алексей VIP Клиент",
                "type": "private",
                "sender_id": "user_client",
                "sender_name": "Алексей VIP",
                "messages": [],
            },
            "chat_spammer": {
                "chat_id": "chat_spammer",
                "title": "Незнакомый Пользователь",
                "type": "private",
                "sender_id": "user_spammer",
                "sender_name": "Crypto Bot / Spammer",
                "messages": [],
            },
        }

    async def connect(self, **kwargs) -> Dict[str, Any]:
        self.is_connected = True
        return {"status": "connected", "mode": "simulator", "account": self.account_info}

    async def disconnect(self) -> Dict[str, Any]:
        self.is_connected = False
        return {"status": "disconnected", "mode": "simulator"}

    async def get_status(self) -> Dict[str, Any]:
        return {
            "is_connected": self.is_connected,
            "mode": "simulator",
            "account": self.account_info if self.is_connected else None,
            "saved_messages_count": len(self.saved_messages),
        }

    async def send_message(self, chat_id: str, text: str, reply_to_msg_id: Optional[str] = None) -> Dict[str, Any]:
        msg_id = f"sim_out_{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.utcnow().isoformat()
        out_msg = {
            "message_id": msg_id,
            "chat_id": chat_id,
            "sender_id": self.account_info["telegram_user_id"],
            "sender_name": self.account_info["first_name"],
            "direction": "outgoing",
            "text": text,
            "reply_to": reply_to_msg_id,
            "timestamp": now,
        }
        if chat_id in self.simulated_chats:
            self.simulated_chats[chat_id]["messages"].append(out_msg)
        return out_msg

    async def send_to_saved_messages(self, text: str) -> Dict[str, Any]:
        msg_id = f"saved_{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.utcnow().isoformat()
        entry = {
            "id": msg_id,
            "text": text,
            "timestamp": now,
            "type": "summary_digest",
        }
        self.saved_messages.insert(0, entry)
        return entry

    async def fetch_dialogs(self) -> List[Dict[str, Any]]:
        return list(self.simulated_chats.values())

    def register_event_listener(self, callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]):
        self._listener = callback

    async def simulate_incoming(
        self,
        chat_id: str,
        sender_id: str,
        sender_name: str,
        text: str,
        chat_title: Optional[str] = None,
        chat_type: str = "private",
    ) -> Dict[str, Any]:
        """Injects a simulated incoming Telegram message."""
        msg_id = f"sim_in_{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.utcnow().isoformat()

        if chat_id not in self.simulated_chats:
            self.simulated_chats[chat_id] = {
                "chat_id": chat_id,
                "title": chat_title or sender_name,
                "type": chat_type,
                "sender_id": sender_id,
                "sender_name": sender_name,
                "messages": [],
            }

        message_payload = {
            "telegram_message_id": msg_id,
            "chat_id": chat_id,
            "chat_title": chat_title or self.simulated_chats[chat_id]["title"],
            "chat_type": chat_type,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "direction": "incoming",
            "text": text,
            "timestamp": now,
        }

        self.simulated_chats[chat_id]["messages"].append(message_payload)

        # Notify registered listener
        if self._listener:
            await self._listener(message_payload)

        return message_payload

simulator_gateway = SimulatorGateway()
