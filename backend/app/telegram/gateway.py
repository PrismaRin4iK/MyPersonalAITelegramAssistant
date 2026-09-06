from abc import ABC, abstractmethod
from typing import Callable, Coroutine, Any, Optional, List, Dict

class TelegramGateway(ABC):
    """Abstract base gateway for Telegram connection (Telethon or Simulator)."""

    @abstractmethod
    async def connect(self, **kwargs) -> Dict[str, Any]:
        """Connects the session or initializes simulator."""
        pass

    @abstractmethod
    async def disconnect(self) -> Dict[str, Any]:
        """Terminates active session."""
        pass

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Returns connection status, user identity, and mode."""
        pass

    @abstractmethod
    async def send_message(self, chat_id: str, text: str, reply_to_msg_id: Optional[str] = None) -> Dict[str, Any]:
        """Sends an outgoing message on behalf of the user."""
        pass

    @abstractmethod
    async def send_to_saved_messages(self, text: str) -> Dict[str, Any]:
        """Delivers a summary, task list, or alert to 'Saved Messages' (Избранное)."""
        pass

    @abstractmethod
    async def fetch_dialogs(self) -> List[Dict[str, Any]]:
        """Returns active dialogs / chats."""
        pass

    @abstractmethod
    def register_event_listener(self, callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]):
        """Registers listener callback for incoming Telegram events."""
        pass
