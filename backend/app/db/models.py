import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    auth_status = Column(String(50), default="active")
    settings_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    telegram_accounts = relationship("TelegramAccount", back_populates="user", cascade="all, delete-orphan")


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_user_id = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    username = Column(String(100), nullable=True)
    phone_number = Column(String(50), nullable=True)
    session_ciphertext = Column(Text, nullable=True)  # Fernet encrypted MTProto session string
    status = Column(String(50), default="disconnected")  # connected, disconnected, connecting, error
    is_simulator = Column(Boolean, default=True)
    last_connected_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="telegram_accounts")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    telegram_chat_id = Column(String(100), unique=True, index=True, nullable=False)
    type = Column(String(50), default="private")  # private, group, supergroup, channel, saved_messages
    title = Column(String(255), nullable=True)
    username = Column(String(100), nullable=True)
    enabled = Column(Boolean, default=True)  # Global toggle for this chat
    auto_reply_enabled = Column(Boolean, default=False)
    summary_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(String(100), unique=True, index=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    username = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    category = Column(String(50), default="colleague")  # colleague, friend, client, stranger, vip
    ai_mode = Column(String(50), default="draft")  # analysis_only, draft, auto_reply, ignored
    profile_id = Column(Integer, ForeignKey("ai_profiles.id"), nullable=True)
    is_whitelisted = Column(Boolean, default=False)
    is_blacklisted = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    profile = relationship("AiProfile")
    memories = relationship("ConversationMemory", back_populates="contact", cascade="all, delete-orphan")
    tasks = relationship("TaskItem", back_populates="contact", cascade="all, delete-orphan")


class AiProfile(Base):
    __tablename__ = "ai_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    system_policy = Column(Text, nullable=False)
    style = Column(String(100), default="friendly")  # friendly, concise, formal, technical
    max_tokens = Column(Integer, default=200)
    forbidden_topics = Column(JSON, default=list)  # ["passwords", "finances", "access tokens"]
    allowed_actions = Column(JSON, default=lambda: ["draft", "summary"])
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    scope = Column(String(50), nullable=False)  # global, user, group, chat_type, category
    subject = Column(String(100), nullable=True)  # e.g. "user:123", "group:dev", "category:stranger"
    action = Column(String(50), nullable=False)  # allow_auto, force_draft, ignore, analysis_only, ban
    priority = Column(Integer, default=100)  # Lower number = higher priority
    conditions = Column(JSON, default=dict)  # {"min_importance": 7, "quiet_hours": false, "auto_reply": true}
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    telegram_message_id = Column(String(100), index=True, nullable=False)
    sender_id = Column(String(100), index=True, nullable=False)
    sender_name = Column(String(255), nullable=True)
    direction = Column(String(20), default="incoming")  # incoming, outgoing
    encrypted_content = Column(Text, nullable=False)  # Fernet encrypted message text
    metadata_json = Column(JSON, default=dict)  # reply_to, date, entities
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")
    analysis = relationship("Analysis", back_populates="message", uselist=False, cascade="all, delete-orphan")
    actions = relationship("ActionItem", back_populates="message", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), unique=True, nullable=False)
    intent = Column(String(100), nullable=False)  # task, question, greeting, update, spam, urgent
    importance = Column(Integer, default=5)  # 1 to 10
    urgency = Column(Integer, default=5)  # 1 to 10
    needs_reply = Column(Boolean, default=False)
    summary = Column(Text, nullable=True)
    topics = Column(JSON, default=list)  # ["JWT", "backend", "login"]
    action_items = Column(JSON, default=list)  # ["Проверить refresh token flow"]
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    message = relationship("Message", back_populates="analysis")


class ConversationMemory(Base):
    __tablename__ = "conversation_memory"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    fact = Column(Text, nullable=False)
    source_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    contact = relationship("Contact", back_populates="memories")


class TaskItem(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    source_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    title = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String(50), default="open")  # open, in_progress, done, dismissed
    due_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    contact = relationship("Contact", back_populates="tasks")


class ActionItem(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    action_type = Column(String(50), nullable=False)  # auto_reply, draft_reply, summary_to_saved, alert
    decision = Column(String(50), nullable=False)  # approved, rejected, executed, pending_approval, blocked
    reason = Column(Text, nullable=True)
    proposed_text = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    status = Column(String(50), default="pending")  # pending, executed, approved, rejected
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    message = relationship("Message", back_populates="actions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String(100), default="system")  # system, user, ai_analyzer, response_guard
    event_type = Column(String(100), nullable=False)  # rule_evaluation, guard_block, auto_reply, draft_created, circuit_tripped
    object = Column(String(100), nullable=True)  # e.g. "chat:12345", "rule:3"
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
