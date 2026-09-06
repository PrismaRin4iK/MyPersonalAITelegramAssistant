import re
from typing import NamedTuple, Optional
from backend.app.config import settings

class GuardResult(NamedTuple):
    is_allowed: bool
    reason: str
    sanitized_text: str

# Prohibited dangerous commands in auto-replies
DANGEROUS_COMMAND_PATTERNS = [
    re.compile(r"^\s*/[a-zA-Z0-9_-]+"),  # Telegram bot commands like /start, /admin
    re.compile(r"(?i)\b(rm\s+-rf|curl\s+|wget\s+|chmod\s+|bash\s+-c|exec\(|eval\()"),  # shell commands
    re.compile(r"(?i)\b(drop\s+table|delete\s+from|insert\s+into|select\s+.*from)\b"),  # SQL injection
    re.compile(r"(?i)\b(transfer\s+\$?\d+|send\s+(money|usdt|crypto|eth|btc))\b"),  # Financial actions
]

# Sensitive credentials that must never be emitted in text
LEAK_PATTERNS = [
    re.compile(r"1[0-9]{8,10}:[a-zA-Z0-9_-]{35}"),  # Telegram Bot Token
    re.compile(r"(?i)(sk-[a-zA-Z0-9]{20,})"),  # OpenAI API keys
    re.compile(r"(?i)(ghp_[a-zA-Z0-9]{20,})"),  # GitHub tokens
    re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),  # JWT
    re.compile(r"(?i)(password\s*[:=]\s*['\"]?\S+['\"]?)"),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"),
]

class ResponseGuard:
    """
    Response Guard sits between Generator and Telegram (Section 14).
    Validates safety, permissions, limits, and secrecy before any outgoing transmission.
    """

    @classmethod
    def validate(
        cls,
        text: str,
        chat_enabled: bool,
        auto_reply_enabled: bool,
        is_whitelisted: bool = False,
        is_blacklisted: bool = False,
        max_length: Optional[int] = None,
        forbidden_topics: Optional[list[str]] = None,
    ) -> GuardResult:
        # Check 1: Chat authorization
        if not chat_enabled:
            return GuardResult(False, "Chat is globally disabled in assistant settings", "")

        # Check 2: Blacklist check
        if is_blacklisted:
            return GuardResult(False, "Recipient is blacklisted from receiving AI responses", "")

        # Check 3: Auto-reply permission
        if not auto_reply_enabled and not is_whitelisted:
            return GuardResult(False, "Auto-reply is not enabled for this contact or chat", "")

        # Check 4: Empty or whitespace
        cleaned = text.strip()
        if not cleaned:
            return GuardResult(False, "Generated response is empty", "")

        # Check 5: Length check
        limit = max_length or settings.MAX_REPLY_LENGTH
        if len(cleaned) > limit:
            return GuardResult(
                False,
                f"Response length ({len(cleaned)}) exceeds maximum permissible limit ({limit})",
                "",
            )

        # Check 6: Dangerous commands
        for pattern in DANGEROUS_COMMAND_PATTERNS:
            if pattern.search(cleaned):
                return GuardResult(
                    False,
                    "Response contains prohibited command or executable syntax",
                    "",
                )

        # Check 7: Credential leaks
        for pattern in LEAK_PATTERNS:
            if pattern.search(cleaned):
                return GuardResult(
                    False,
                    "Response blocked by leak prevention: sensitive credential pattern detected",
                    "",
                )

        # Check 8: Forbidden topics from AI Profile
        if forbidden_topics:
            lower_text = cleaned.lower()
            for topic in forbidden_topics:
                if topic.lower() in lower_text:
                    return GuardResult(
                        False,
                        f"Response mentions forbidden topic: '{topic}'",
                        "",
                    )

        # Check 9: Meta-prompt override / instruction leak
        if "SYSTEM POLICY" in cleaned or "IGNORE ALL PREVIOUS INSTRUCTIONS" in cleaned.upper():
            return GuardResult(
                False,
                "Response contains prompt injection or system override artifact",
                "",
            )

        return GuardResult(True, "Response passed all safety and policy checks", cleaned)
