import asyncio
import io
import json
import urllib.parse
import logging
from typing import Callable, Coroutine, Any, Optional, List, Dict
import qrcode
import qrcode.image.svg
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from backend.app.config import settings
from backend.app.security.crypto import encrypt_text, decrypt_text
from backend.app.telegram.gateway import TelegramGateway

logger = logging.getLogger(__name__)

def parse_telethon_error(e: Exception) -> str:
    err_name = type(e).__name__
    err_msg = str(e)

    if "SendCodeUnavailable" in err_name or "SendCodeUnavailable" in err_msg:
        return (
            "Telegram временно ограничил отправку кода для этого номера (SendCodeUnavailable). "
            "Это происходит из-за нескольких частых запросов подряд или если Telegram ожидает повторную отправку позже. "
            "Пожалуйста, подождите 10-15 минут перед следующей попыткой или проверьте входящие уведомления в приложении Telegram."
        )
    elif "ApiIdInvalid" in err_name or "ApiIdInvalid" in err_msg:
        return "Неверный API ID или API HASH. Проверьте правильность введенных ключей с сайта my.telegram.org."
    elif "PhoneNumberInvalid" in err_name or "PhoneNumberInvalid" in err_msg:
        return "Некорректный номер телефона. Укажите номер в международном формате, например: +79991234567."
    elif "PhoneNumberBanned" in err_name or "PhoneNumberBanned" in err_msg:
        return "Этот номер телефона заблокирован в Telegram."
    elif "FloodWait" in err_name or "FloodWait" in err_msg:
        seconds = getattr(e, "seconds", 60)
        return f"Слишком много попыток входа! Telegram просит подождать {seconds} секунд перед повторным запросом."
    elif "PhoneCodeExpired" in err_name or "PhoneCodeExpired" in err_msg:
        return "Срок действия кода подтверждения истек. Запросите код заново."
    elif "PhoneCodeInvalid" in err_name or "PhoneCodeInvalid" in err_msg:
        return "Введен неверный код подтверждения из Telegram."
    elif "PasswordHashInvalid" in err_name or "PasswordHashInvalid" in err_msg:
        return "Введен неверный 2FA облачный пароль Telegram."

    return f"{err_name}: {err_msg}"

class TelethonGateway(TelegramGateway):
    """
    Production MTProto Telegram Client Gateway using Telethon.
    Manages user authentication, session encryption, incoming events, and message sending.
    """

    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.session_str: str = ""
        self.phone_code_hash: Optional[str] = None
        self.pending_phone: Optional[str] = None
        self._listener: Optional[Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]] = None
        self._is_connected: bool = False
        self._qr_login = None
        self._qr_task: Optional[asyncio.Task] = None
        self._qr_requires_2fa: bool = False

    def register_event_listener(self, callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]):
        self._listener = callback

    async def connect(
        self,
        api_id: Optional[int] = None,
        api_hash: Optional[str] = None,
        session_encrypted: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Connects using an existing encrypted session or initializes a new client."""
        app_id = api_id or settings.TELEGRAM_API_ID
        app_hash = api_hash or settings.TELEGRAM_API_HASH

        if not app_id or not app_hash:
            return {
                "success": False,
                "error": "Missing api_id or api_hash. Please configure Telegram credentials in settings.",
            }

        session_plain = ""
        if session_encrypted:
            session_plain = decrypt_text(session_encrypted)

        self.client = TelegramClient(StringSession(session_plain), app_id, app_hash)
        await self.client.connect()

        if await self.client.is_user_authorized():
            self._is_connected = True
            me = await self.client.get_me()
            self._setup_event_handlers()
            exported_session = self.client.session.save()
            self._save_credentials(app_id, app_hash, exported_session)
            return {
                "success": True,
                "authorized": True,
                "user": {
                    "id": str(me.id),
                    "username": me.username,
                    "first_name": me.first_name,
                    "phone": me.phone,
                },
                "encrypted_session": encrypt_text(exported_session),
            }
        else:
            return {
                "success": True,
                "authorized": False,
                "message": "Client connected but requires authentication (phone code or QR).",
            }

    def _save_credentials(self, api_id: int, api_hash: str, exported_session: str):
        try:
            session_file = settings.DATA_DIR / "session_credentials.json"
            data = {
                "api_id": api_id,
                "api_hash": api_hash,
                "encrypted_session": encrypt_text(exported_session),
            }
            with open(session_file, "w") as f:
                json.dump(data, f)
            logger.info("Saved encrypted Telegram session credentials to disk")
        except Exception as e:
            logger.error(f"Failed to save session credentials: {e}")

    def _clear_credentials(self):
        try:
            session_file = settings.DATA_DIR / "session_credentials.json"
            if session_file.exists():
                session_file.unlink()
            logger.info("Cleared Telegram session credentials from disk")
        except Exception as e:
            logger.error(f"Failed to clear session credentials: {e}")

    async def auto_reconnect(self) -> bool:
        """Attempts to reconnect using saved encrypted credentials from disk."""
        if self._is_connected and self.client:
            return True

        session_file = settings.DATA_DIR / "session_credentials.json"
        if not session_file.exists():
            return False

        try:
            with open(session_file, "r") as f:
                data = json.load(f)
            api_id = data.get("api_id")
            api_hash = data.get("api_hash")
            encrypted_session = data.get("encrypted_session")
            if api_id and api_hash and encrypted_session:
                res = await self.connect(api_id=api_id, api_hash=api_hash, session_encrypted=encrypted_session)
                return res.get("authorized", False)
        except Exception as e:
            logger.error(f"Auto-reconnect error: {e}")
        return False

    async def request_phone_code(self, phone: str, api_id: int, api_hash: str) -> Dict[str, Any]:
        """Initiates official Telegram phone login flow with phone normalization and error handling."""
        try:
            if self.client:
                try:
                    await self.client.disconnect()
                except Exception:
                    pass

            # Clean and normalize phone number format
            cleaned = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            if cleaned.startswith("8") and len(cleaned) == 11:
                cleaned = "+7" + cleaned[1:]
            elif not cleaned.startswith("+"):
                cleaned = "+" + cleaned

            self.client = TelegramClient(StringSession(""), api_id, api_hash)
            await self.client.connect()
            sent = await self.client.send_code_request(cleaned)
            self.pending_phone = cleaned
            self.phone_code_hash = sent.phone_code_hash
            return {
                "success": True,
                "phone": cleaned,
                "phone_code_hash": sent.phone_code_hash,
                "timeout": getattr(sent, "timeout", 120),
            }
        except Exception as e:
            logger.error(f"Error requesting Telegram phone code for {phone}: {e}", exc_info=True)
            return {
                "success": False,
                "error": parse_telethon_error(e),
            }

    async def request_qr_login(self, api_id: int, api_hash: str) -> Dict[str, Any]:
        """Generates a Telegram QR code login token for scanning with Telegram mobile app."""
        try:
            if self._qr_task and not self._qr_task.done():
                self._qr_task.cancel()

            if self.client:
                try:
                    await self.client.disconnect()
                except Exception:
                    pass

            self._qr_requires_2fa = False
            self.client = TelegramClient(StringSession(""), api_id, api_hash)
            await self.client.connect()
            self._qr_login = await self.client.qr_login()
            token_url = self._qr_login.url

            # Generate offline vector SVG QR code (works 100% locally)
            img = qrcode.make(token_url, image_factory=qrcode.image.svg.SvgImage)
            buf = io.BytesIO()
            img.save(buf)
            svg_data = buf.getvalue().decode("utf-8")
            qr_image_url = f"data:image/svg+xml;utf8,{urllib.parse.quote(svg_data)}"

            # Run Telethon wait() as non-blocking background worker
            self._qr_task = asyncio.create_task(self._qr_wait_worker())

            return {
                "success": True,
                "token_url": token_url,
                "qr_image_url": qr_image_url,
            }
        except Exception as e:
            logger.error(f"Error initiating QR code login: {e}", exc_info=True)
            return {
                "success": False,
                "error": parse_telethon_error(e),
            }

    async def _qr_wait_worker(self):
        """Background worker to wait for QR code scan without blocking event loop."""
        try:
            await self._qr_login.wait()
            if await self.client.is_user_authorized():
                me = await self.client.get_me()
                self._is_connected = True
                self._setup_event_handlers()
        except Exception as e:
            if "SessionPasswordNeeded" in type(e).__name__ or "Two-steps verification" in str(e):
                self._qr_requires_2fa = True
            else:
                logger.error(f"QR login wait error: {e}")

    async def check_qr_login(self) -> Dict[str, Any]:
        """Non-blocking check if QR code was scanned by Telegram app."""
        if not self.client or not self._qr_login:
            return {"success": False, "error": "No QR login flow in progress"}

        try:
            if self._qr_requires_2fa:
                return {"success": False, "requires_2fa": True, "error": "2FA password required"}

            if await self.client.is_user_authorized():
                me = await self.client.get_me()
                self._is_connected = True
                self._setup_event_handlers()
                exported = self.client.session.save()
                return {
                    "success": True,
                    "authorized": True,
                    "user": {
                        "id": str(me.id),
                        "username": me.username,
                        "first_name": me.first_name,
                        "phone": me.phone,
                    },
                    "encrypted_session": encrypt_text(exported),
                }

            return {"success": True, "authorized": False, "waiting": True}
        except Exception as e:
            return {"success": False, "error": parse_telethon_error(e)}

    async def complete_phone_login(self, code: Optional[str] = None, password_2fa: Optional[str] = None) -> Dict[str, Any]:
        """Submits phone code (and/or 2FA password if required) to finalize login."""
        if not self.client:
            return {"success": False, "error": "No active Telegram client login flow in progress"}

        try:
            if code and self.pending_phone:
                await self.client.sign_in(self.pending_phone, code, phone_code_hash=self.phone_code_hash)
            elif password_2fa:
                await self.client.sign_in(password=password_2fa)
            else:
                return {"success": False, "error": "Either code or password_2fa is required"}
        except Exception as e:
            if "Two-steps verification" in str(e) or "SessionPasswordNeeded" in type(e).__name__:
                if not password_2fa:
                    return {"success": False, "requires_2fa": True, "error": "2FA password required"}
                try:
                    await self.client.sign_in(password=password_2fa)
                except Exception as p_err:
                    return {"success": False, "error": parse_telethon_error(p_err)}
            else:
                return {"success": False, "error": parse_telethon_error(e)}

        me = await self.client.get_me()
        self._is_connected = True
        self._setup_event_handlers()
        exported = self.client.session.save()
        self._save_credentials(self.client.api_id, self.client.api_hash, exported)

        return {
            "success": True,
            "authorized": True,
            "user": {
                "id": str(me.id),
                "username": me.username,
                "first_name": me.first_name,
                "phone": me.phone,
            },
            "encrypted_session": encrypt_text(exported),
        }

    def _setup_event_handlers(self):
        if not self.client:
            return

        @self.client.on(events.NewMessage(incoming=True))
        async def incoming_handler(event):
            try:
                # Do not process outgoing or self-sent messages
                if event.out:
                    return

                sender = await event.get_sender()
                chat = await event.get_chat()

                sender_id = str(sender.id if sender else (event.sender_id or "unknown"))
                sender_name = getattr(sender, "first_name", "") or getattr(sender, "title", "User")
                chat_id = str(chat.id if chat else (event.chat_id or "unknown"))
                chat_title = getattr(chat, "title", sender_name)
                chat_type = "private" if event.is_private else ("group" if event.is_group else "channel")

                payload = {
                    "telegram_message_id": str(event.message.id),
                    "chat_id": chat_id,
                    "chat_title": chat_title,
                    "chat_type": chat_type,
                    "sender_id": sender_id,
                    "sender_name": sender_name,
                    "direction": "incoming",
                    "text": event.message.message or "",
                    "timestamp": event.message.date.isoformat(),
                }

                if self._listener:
                    await self._listener(payload)
            except Exception as e:
                logger.error(f"Error processing incoming Telethon message: {e}", exc_info=True)

    async def disconnect(self) -> Dict[str, Any]:
        if self.client:
            await self.client.disconnect()
            self._is_connected = False
        self._clear_credentials()
        return {"status": "disconnected"}

    async def get_status(self) -> Dict[str, Any]:
        if not self.client or not self._is_connected:
            await self.auto_reconnect()

        if not self.client or not self._is_connected:
            return {"is_connected": False, "mode": "telethon"}

        try:
            me = await self.client.get_me()
            return {
                "is_connected": True,
                "mode": "telethon",
                "account": {
                    "telegram_user_id": str(me.id),
                    "username": me.username,
                    "first_name": me.first_name,
                    "phone": me.phone,
                    "is_simulator": False,
                },
            }
        except Exception:
            return {"is_connected": False, "mode": "telethon"}

    async def send_message(self, chat_id: str, text: str, reply_to_msg_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.client or not self._is_connected:
            raise RuntimeError("Telethon client is not connected")

        target = int(chat_id) if (chat_id.startswith("-") or chat_id.isdigit()) else chat_id
        reply_id = int(reply_to_msg_id) if (reply_to_msg_id and reply_to_msg_id.isdigit()) else None

        # Resolve entity safely
        target_entity = target
        try:
            target_entity = await self.client.get_entity(target)
        except Exception:
            try:
                target_entity = await self.client.get_input_entity(target)
            except Exception:
                target_entity = target

        try:
            sent = await self.client.send_message(target_entity, text, reply_to=reply_id)
        except Exception as send_err:
            if reply_id:
                logger.warning(f"Failed sending message with reply_to={reply_id}, retrying without reply_to: {send_err}")
                sent = await self.client.send_message(target_entity, text)
            else:
                raise send_err

        logger.info(f"Telethon successfully sent message {sent.id} to chat {chat_id}")
        return {
            "message_id": str(sent.id),
            "chat_id": str(chat_id),
            "text": text,
            "timestamp": sent.date.isoformat(),
            "direction": "outgoing",
        }

    async def send_to_saved_messages(self, text: str) -> Dict[str, Any]:
        if not self.client or not self._is_connected:
            raise RuntimeError("Telethon client is not connected")

        sent = await self.client.send_message("me", text)
        return {
            "id": str(sent.id),
            "text": text,
            "timestamp": sent.date.isoformat(),
            "type": "saved_messages",
        }

    @property
    def is_connected(self) -> bool:
        return bool(self._is_connected and self.client)

    async def fetch_dialogs(self) -> List[Dict[str, Any]]:
        if not self.client or not self._is_connected:
            return []

        dialogs = []
        async for d in self.client.iter_dialogs(limit=30):
            dialogs.append({
                "chat_id": str(d.id),
                "title": d.name,
                "type": "private" if d.is_user else ("group" if d.is_group else "channel"),
                "unread_count": d.unread_count,
            })
        return dialogs

    async def fetch_contacts(self) -> List[Dict[str, Any]]:
        """
        Fetches Telegram contacts from address book and recent active private dialogs.
        Filters out bots, deleted accounts, and self.
        """
        if not self.client or not self._is_connected:
            return []

        from telethon.tl.functions.contacts import GetContactsRequest
        from telethon.tl.types import User

        seen_ids = set()
        contacts_list = []

        try:
            me = await self.client.get_me()
            my_id = me.id if me else None
        except Exception:
            my_id = None

        # 1. Fetch from Telegram address book
        try:
            res = await self.client(GetContactsRequest(hash=0))
            if hasattr(res, "users"):
                for u in res.users:
                    if isinstance(u, User) and not u.bot and not getattr(u, "deleted", False) and u.id != my_id:
                        if u.id not in seen_ids:
                            seen_ids.add(u.id)
                            first = u.first_name or ""
                            last = u.last_name or ""
                            name = f"{first} {last}".strip() or u.username or f"User {u.id}"
                            contacts_list.append({
                                "telegram_user_id": str(u.id),
                                "display_name": name,
                                "username": u.username or "",
                                "phone": u.phone or "",
                                "is_contact": True,
                            })
        except Exception as e:
            logger.warning(f"Failed to fetch address book contacts: {e}")

        # 2. Also fetch recent active private dialogs
        try:
            async for d in self.client.iter_dialogs(limit=60):
                if d.is_user and d.entity and not getattr(d.entity, "bot", False) and not getattr(d.entity, "deleted", False):
                    uid = d.entity.id
                    if uid != my_id and uid not in seen_ids:
                        seen_ids.add(uid)
                        first = getattr(d.entity, "first_name", "") or ""
                        last = getattr(d.entity, "last_name", "") or ""
                        name = f"{first} {last}".strip() or getattr(d.entity, "username", "") or d.name or f"User {uid}"
                        contacts_list.append({
                            "telegram_user_id": str(uid),
                            "display_name": name,
                            "username": getattr(d.entity, "username", "") or "",
                            "phone": getattr(d.entity, "phone", "") or "",
                            "is_contact": getattr(d.entity, "contact", False),
                        })
        except Exception as e:
            logger.warning(f"Failed to iter dialogs for contacts: {e}")

        return contacts_list

telethon_gateway = TelethonGateway()
