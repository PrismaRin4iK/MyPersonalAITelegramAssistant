import time
from typing import Dict, List, Tuple
from backend.app.config import settings

class CircuitBreaker:
    """
    Manages rate limits, cooldowns, and emergency circuit breaking (Section 15).
    Protects the Telegram account against ban, infinite reply loops, or rapid error cascades.
    """

    def __init__(self):
        self._is_tripped: bool = False
        self._trip_reason: str = ""
        self._tripped_at: float = 0.0

        # In-memory sliding windows: timestamp lists
        self._global_replies: List[float] = []
        self._chat_replies: Dict[str, List[float]] = {}
        self._last_reply_time_by_chat: Dict[str, float] = {}
        self._errors_window: List[float] = []

        # Configs
        self.chat_limit_per_min = settings.RATE_LIMIT_PER_MINUTE_CHAT
        self.global_limit_per_min = settings.RATE_LIMIT_PER_MINUTE_GLOBAL
        self.cooldown_seconds = 15  # Minimum seconds between replies to same chat
        self.error_threshold = settings.CIRCUIT_BREAKER_ERROR_THRESHOLD
        self.window_seconds = settings.CIRCUIT_BREAKER_WINDOW_SECONDS

    def is_tripped(self) -> bool:
        return self._is_tripped

    def get_trip_info(self) -> Tuple[bool, str, float]:
        return self._is_tripped, self._trip_reason, self._tripped_at

    def trip(self, reason: str):
        self._is_tripped = True
        self._trip_reason = reason
        self._tripped_at = time.time()

    def reset(self):
        self._is_tripped = False
        self._trip_reason = ""
        self._tripped_at = 0.0
        self._errors_window.clear()

    def record_error(self, error_desc: str) -> bool:
        """Records an error. Returns True if this triggered a circuit trip."""
        now = time.time()
        self._errors_window = [t for t in self._errors_window if now - t < self.window_seconds]
        self._errors_window.append(now)

        if len(self._errors_window) >= self.error_threshold:
            self.trip(f"Error spike: {len(self._errors_window)} failures in {self.window_seconds}s ({error_desc})")
            return True
        return False

    def check_can_reply(self, chat_id: str) -> Tuple[bool, str]:
        """
        Validates whether an auto-reply is currently allowed under rate limits, cooldown, and circuit breaker.
        """
        now = time.time()

        # 1. Circuit breaker trip check
        if self._is_tripped:
            return False, f"Circuit breaker is TRIPPED: {self._trip_reason}"

        # 2. Cooldown check for this chat
        last_reply = self._last_reply_time_by_chat.get(chat_id, 0.0)
        if now - last_reply < self.cooldown_seconds:
            remaining = int(self.cooldown_seconds - (now - last_reply))
            return False, f"Chat cooldown active: please wait {remaining}s"

        # 3. Chat rate limit
        history = [t for t in self._chat_replies.get(chat_id, []) if now - t < 60.0]
        self._chat_replies[chat_id] = history
        if len(history) >= self.chat_limit_per_min:
            return False, f"Chat rate limit exceeded ({len(history)}/{self.chat_limit_per_min} per min)"

        # 4. Global rate limit
        self._global_replies = [t for t in self._global_replies if now - t < 60.0]
        if len(self._global_replies) >= self.global_limit_per_min:
            self.trip(f"Global auto-reply rate limit exceeded ({self.global_limit_per_min} per min)")
            return False, "Global rate limit exceeded; circuit breaker tripped for safety"

        return True, "Rate limits and cooldown satisfied"

    def record_reply_sent(self, chat_id: str):
        """Registers that a reply was successfully sent."""
        now = time.time()
        self._last_reply_time_by_chat[chat_id] = now
        self._global_replies.append(now)

        if chat_id not in self._chat_replies:
            self._chat_replies[chat_id] = []
        self._chat_replies[chat_id].append(now)

circuit_breaker = CircuitBreaker()
