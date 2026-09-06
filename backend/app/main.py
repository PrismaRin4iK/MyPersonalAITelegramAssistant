import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from backend.app.config import settings
from backend.app.db.database import init_db, AsyncSessionLocal
from backend.app.db.models import AiProfile, Rule, Contact, Chat, User
from backend.app.security.auth import hash_password
from backend.workers.pipeline import message_pipeline

# Import Routers
from backend.app.api.routes_auth import router as auth_router
from backend.app.api.routes_telegram import router as telegram_router
from backend.app.api.routes_chats import router as chats_router
from backend.app.api.routes_contacts import router as contacts_router
from backend.app.api.routes_rules import router as rules_router
from backend.app.api.routes_profiles import router as profiles_router
from backend.app.api.routes_messages import router as messages_router
from backend.app.api.routes_actions import router as actions_router
from backend.app.api.routes_summaries import router as summaries_router
from backend.app.api.routes_ai import router as ai_router
from backend.app.api.routes_categories import router as categories_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_initial_data():
    """Populates database with default AI profiles, rules, and demo contacts if clean."""
    async with AsyncSessionLocal() as session:
        # 1. Admin user
        user_res = await session.execute(select(User))
        if not user_res.scalars().first():
            admin_user = User(
                username="admin",
                hashed_password=hash_password("admin"),
                auth_status="active",
            )
            session.add(admin_user)

        # 2. AI Profiles
        prof_res = await session.execute(select(AiProfile))
        if not prof_res.scalars().first():
            p_dev = AiProfile(
                name="Коллеги (Разработка)",
                description="Дружелюбный и технический тон для команды разработки",
                system_policy="Ты персональный ассистент инженера. Отвечай дружелюбно, по существу, помогай с задачами разработки. Не обещай невыполнимых сроков.",
                style="friendly",
                max_tokens=200,
                forbidden_topics=["пароли", "доступ к прод БД", "зарплаты"],
                is_default=True,
            )
            p_formal = AiProfile(
                name="Клиенты (Деловой)",
                description="Сдержанный, вежливый деловой стиль",
                system_policy="Деловой стиль, вежливость, акцент на сроки и соглашения.",
                style="formal",
                max_tokens=250,
                forbidden_topics=["внутренние баги", "конфиденциальные оценки"],
                is_default=False,
            )
            session.add_all([p_dev, p_formal])
            await session.flush()

        # 3. Rules (Default safety and channel policies)
        rule_res = await session.execute(select(Rule))
        if not rule_res.scalars().first():
            rule_close = Rule(
                name="Близкие (close) — Автоответ без задержек",
                scope="category",
                subject="category:close",
                action="allow_auto",
                priority=20,
                conditions={
                    "analysis": True,
                    "auto_reply": True,
                    "summary": True,
                    "min_importance": 6,
                    "require_draft_approval": False,
                },
                is_active=True,
            )
            rule_family = Rule(
                name="Семья (family) — Автоответ и уведомления",
                scope="category",
                subject="category:family",
                action="allow_auto",
                priority=25,
                conditions={
                    "analysis": True,
                    "auto_reply": True,
                    "summary": True,
                    "min_importance": 6,
                    "require_draft_approval": False,
                },
                is_active=True,
            )
            rule_stranger = Rule(
                name="Незнакомые пользователи — Только анализ & Черновик",
                scope="category",
                subject="category:stranger",
                action="force_draft",
                priority=80,
                conditions={
                    "analysis": True,
                    "auto_reply": False,
                    "summary": True,
                    "min_importance": 8,
                    "require_draft_approval": True,
                },
                is_active=True,
            )
            rule_channels = Rule(
                name="Telegram Каналы — Только чтение и дайджесты",
                scope="chat_type",
                subject="type:channel",
                action="analysis_only",
                priority=10,
                conditions={
                    "analysis": True,
                    "auto_reply": False,
                    "summary": True,
                    "min_importance": 8,
                },
                is_active=True,
            )
            session.add_all([rule_close, rule_family, rule_stranger, rule_channels])

        await session.commit()

from backend.app.telegram.telethon_client import telethon_gateway

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Assistant Database...")
    await init_db()
    await seed_initial_data()
    logger.info("Attempting Telegram auto-reconnect from saved session...")
    await telethon_gateway.auto_reconnect()
    logger.info("Starting Message Pipeline Worker...")
    message_pipeline.start()
    yield
    # Shutdown
    logger.info("Shutting down Message Pipeline Worker...")
    await message_pipeline.stop()

app = FastAPI(
    title=settings.APP_NAME,
    description="Personal AI Assistant for Telegram User Account",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth_router, prefix="/api")
app.include_router(telegram_router, prefix="/api")
app.include_router(chats_router, prefix="/api")
app.include_router(contacts_router, prefix="/api")
app.include_router(rules_router, prefix="/api")
app.include_router(profiles_router, prefix="/api")
app.include_router(messages_router, prefix="/api")
app.include_router(actions_router, prefix="/api")
app.include_router(summaries_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(categories_router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}
