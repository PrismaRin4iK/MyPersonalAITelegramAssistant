import asyncio
import logging
from typing import Dict, Any, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.database import AsyncSessionLocal
from backend.app.db.models import Chat, Contact, Message, Analysis, ActionItem, AuditLog, Rule, AiProfile
from backend.app.security.crypto import encrypt_text, decrypt_text
from backend.app.security.guard import ResponseGuard
from backend.app.security.circuit_breaker import circuit_breaker
from backend.app.rules.engine import RuleEngine
from backend.app.ai.analyzer import AIAnalyzer
from backend.app.ai.generator import ResponseGenerator
from backend.app.summaries.service import SummaryService
from backend.app.memory.manager import MemoryManager
from backend.app.categories.service import CategoriesService
from backend.app.telegram.service import telegram_service
from backend.app.telegram.telethon_client import telethon_gateway

logger = logging.getLogger(__name__)

class MessagePipeline:
    """
    Asynchronous queue and worker pipeline (Section 13).
    Ensures Telegram listeners never block on AI latency and provides
    strict idempotency, circuit breaking, deterministic rule evaluation, and response guarding.
    """

    def __init__(self):
        self.queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self.processed_idempotency_keys: Set[str] = set()
        self._worker_task: asyncio.Task | None = None
        self.is_running: bool = False

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._worker_task = asyncio.create_task(self._worker_loop())
            # Register event listener for telethon gateway
            telethon_gateway.register_event_listener(self.enqueue_event)
            logger.info("Message pipeline and event listeners started")

    async def stop(self):
        self.is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def enqueue_event(self, event_data: Dict[str, Any]):
        """Fast non-blocking event listener ingestion."""
        await self.queue.put(event_data)

    async def _worker_loop(self):
        """Worker background loop consuming normalized events."""
        while self.is_running:
            try:
                event = await self.queue.get()
                await self._process_single_event(event)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker unhandled error in pipeline: {e}", exc_info=True)
                circuit_breaker.record_error(str(e))
                await asyncio.sleep(1.0)

    async def _process_single_event(self, event: Dict[str, Any]):
        chat_id = str(event.get("chat_id", ""))
        msg_id = str(event.get("telegram_message_id", ""))
        sender_id = str(event.get("sender_id", ""))
        sender_name = str(event.get("sender_name", "User"))
        chat_title = str(event.get("chat_title", sender_name))
        chat_type = str(event.get("chat_type", "private"))
        raw_text = str(event.get("text", "")).strip()

        # Section 13: Idempotency check (chat_id + msg_id + action_type)
        idempotency_key = f"{chat_id}:{msg_id}:inbound"
        if idempotency_key in self.processed_idempotency_keys:
            logger.warning(f"Duplicate event ignored by idempotency key: {idempotency_key}")
            return
        self.processed_idempotency_keys.add(idempotency_key)

        async with AsyncSessionLocal() as session:
            try:
                # 1. Ensure Chat exists in DB
                chat_res = await session.execute(select(Chat).where(Chat.telegram_chat_id == chat_id))
                chat = chat_res.scalar_one_or_none()
                if not chat:
                    chat = Chat(
                        telegram_chat_id=chat_id,
                        title=chat_title,
                        type=chat_type,
                        enabled=True,
                        auto_reply_enabled=False,
                    )
                    session.add(chat)
                    await session.flush()

                # 2. Ensure Contact exists in DB
                contact_res = await session.execute(select(Contact).where(Contact.telegram_user_id == sender_id))
                contact = contact_res.scalar_one_or_none()
                if not contact:
                    category = "colleague" if "Петров" in sender_name or "Разработка" in chat_title else "stranger"
                    contact = Contact(
                        telegram_user_id=sender_id,
                        display_name=sender_name,
                        category=category,
                        ai_mode="draft",
                    )
                    session.add(contact)
                    await session.flush()

                # 3. Store encrypted Message
                enc_content = encrypt_text(raw_text)
                db_msg = Message(
                    chat_id=chat.id,
                    telegram_message_id=msg_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    direction="incoming",
                    encrypted_content=enc_content,
                    metadata_json={"preview_text": raw_text[:120], "raw_length": len(raw_text)},
                )
                session.add(db_msg)
                await session.flush()

                # 4. Fetch Rules for Rule Engine
                rules_res = await session.execute(select(Rule).where(Rule.is_active == True))
                rules = rules_res.scalars().all()

                # Evaluate Rule Engine
                decision = RuleEngine.evaluate(
                    sender_id=sender_id,
                    chat_id=chat_id,
                    chat_type=chat_type,
                    contact=contact,
                    chat=chat,
                    rules=rules,
                )

                # Audit rule evaluation
                session.add(AuditLog(
                    actor="rule_engine",
                    event_type="rule_evaluated",
                    object=f"message:{db_msg.id}",
                    metadata_json={
                        "rule": decision.matched_rule,
                        "auto_reply_allowed": decision.auto_reply_allowed,
                        "requires_draft": decision.requires_draft_approval,
                        "summary_allowed": decision.summary_allowed,
                    }
                ))

                if not decision.analysis_allowed:
                    await session.commit()
                    return

                # 5. Execute AI Analyzer with retry / backoff
                analysis_res = None
                for attempt in range(3):
                    try:
                        analysis_res = await AIAnalyzer.analyze(raw_text, sender_name, chat_title)
                        break
                    except Exception as e:
                        if attempt == 2:
                            raise e
                        await asyncio.sleep(0.5 * (attempt + 1))

                if not analysis_res:
                    await session.commit()
                    return

                # Persist Analysis
                db_analysis = Analysis(
                    message_id=db_msg.id,
                    intent=analysis_res.intent,
                    importance=analysis_res.importance,
                    urgency=analysis_res.urgency,
                    needs_reply=analysis_res.needs_reply,
                    summary=analysis_res.summary,
                    topics=analysis_res.topics,
                    action_items=analysis_res.action_items,
                )
                session.add(db_analysis)
                await session.flush()

                # Record contact memory facts and tasks
                await MemoryManager.record_contact_facts(
                    session=session,
                    contact_id=contact.id,
                    source_message_id=db_msg.id,
                    topics=analysis_res.topics,
                    action_items=analysis_res.action_items,
                )

                # 6. Summary Service: Instant summary to Saved Messages if threshold met
                if decision.summary_allowed and analysis_res.importance >= decision.min_importance_for_summary:
                    try:
                        await SummaryService.send_instant_summary(
                            sender_name=sender_name,
                            chat_title=chat_title,
                            analysis=db_analysis,
                            raw_text=raw_text,
                        )
                        session.add(AuditLog(
                            actor="summary_service",
                            event_type="instant_summary_dispatched",
                            object="saved_messages",
                            metadata_json={"importance": analysis_res.importance, "summary": analysis_res.summary},
                        ))
                    except Exception as summary_err:
                        logger.warning(f"Could not send instant summary to Saved Messages: {summary_err}")

                # 7. Response Flow: Draft or Auto-reply
                should_respond = (
                    decision.analysis_allowed
                    and analysis_res.intent != "spam"
                    and (
                        decision.auto_reply_allowed
                        or decision.requires_draft_approval
                        or analysis_res.needs_reply
                    )
                )

                if should_respond:
                    # Fetch contact memory context
                    facts, tasks = await MemoryManager.get_contact_context(session, contact.id)

                    # Fetch recent message history in this chat (last 4 messages for natural context)
                    recent_db_msgs = (await session.execute(
                        select(Message)
                        .where(Message.chat_id == db_msg.chat_id, Message.id < db_msg.id)
                        .order_by(Message.id.desc())
                        .limit(4)
                    )).scalars().all()
                    recent_dialog = []
                    for m in reversed(recent_db_msgs):
                        txt = ""
                        if m.encrypted_content:
                            try:
                                txt = decrypt_text(m.encrypted_content)
                            except Exception:
                                txt = (m.metadata_json or {}).get("preview_text", "")
                        recent_dialog.append({"sender": m.sender_name, "text": txt})

                    # Determine category and its prompt instruction
                    category_slug = contact.category or "colleague"
                    cat_info = CategoriesService.get_category(category_slug)
                    category_name = cat_info["name"] if cat_info else category_slug
                    category_instruction = cat_info["prompt_instruction"] if cat_info else ""

                    # Determine style, policy and forbidden topics from profile
                    style = "friendly"
                    system_policy = "Будь вежливым, естественным и лаконичным."
                    forbidden_topics = ["пароли", "токены", "ключи доступа", "финансовые данные"]
                    if contact.profile:
                        style = contact.profile.style or style
                        system_policy = contact.profile.system_policy or system_policy
                        if contact.profile.forbidden_topics:
                            forbidden_topics = contact.profile.forbidden_topics

                    generated_text = await ResponseGenerator.generate_response(
                        incoming_text=raw_text,
                        sender_name=sender_name,
                        style=style,
                        system_policy=system_policy,
                        recent_messages=recent_dialog,
                        contact_facts=facts,
                        unclosed_tasks=tasks,
                        forbidden_topics=forbidden_topics,
                        category=category_slug,
                        category_name=category_name,
                        category_instruction=category_instruction,
                        matched_rule=decision.matched_rule,
                        rule_reason=decision.reason,
                    )

                    if decision.requires_draft_approval:
                        # Create pending action in approval queue (Stage 2)
                        action_item = ActionItem(
                            message_id=db_msg.id,
                            action_type="draft_reply",
                            decision="pending_approval",
                            reason=decision.reason,
                            proposed_text=generated_text,
                            status="pending",
                        )
                        session.add(action_item)
                        session.add(AuditLog(
                            actor="response_generator",
                            event_type="draft_created",
                            object=f"message:{db_msg.id}",
                            metadata_json={"proposed_text": generated_text[:80]},
                        ))

                    elif decision.auto_reply_allowed:
                        # Auto-reply mode (Stage 3): Check Circuit Breaker and Response Guard
                        can_reply, cb_reason = circuit_breaker.check_can_reply(chat_id)
                        if not can_reply:
                            session.add(ActionItem(
                                message_id=db_msg.id,
                                action_type="auto_reply",
                                decision="blocked",
                                reason=cb_reason,
                                proposed_text=generated_text,
                                status="blocked",
                            ))
                        else:
                            # Response Guard check
                            guard = ResponseGuard.validate(
                                text=generated_text,
                                chat_enabled=chat.enabled,
                                auto_reply_enabled=True,
                                is_whitelisted=contact.is_whitelisted,
                                is_blacklisted=contact.is_blacklisted,
                            )

                            if guard.is_allowed:
                                gateway = telegram_service.active_gateway
                                logger.info(f"Dispatching auto-reply via {gateway.__class__.__name__} to chat_id={chat_id}: '{guard.sanitized_text[:60]}'")
                                send_res = await gateway.send_message(
                                    chat_id=chat_id,
                                    text=guard.sanitized_text,
                                    reply_to_msg_id=msg_id,
                                )
                                logger.info(f"Auto-reply successfully delivered to chat_id={chat_id}: {send_res}")
                                circuit_breaker.record_reply_sent(chat_id)

                                session.add(ActionItem(
                                    message_id=db_msg.id,
                                    action_type="auto_reply",
                                    decision="executed",
                                    reason="Auto-reply passed all rules and response guard",
                                    proposed_text=guard.sanitized_text,
                                    result=f"Sent via {gateway.__class__.__name__}",
                                    status="executed",
                                ))
                                session.add(AuditLog(
                                    actor="response_guard",
                                    event_type="auto_reply_sent",
                                    object=f"chat:{chat_id}",
                                    metadata_json={"text": guard.sanitized_text[:80]},
                                ))
                            else:
                                session.add(ActionItem(
                                    message_id=db_msg.id,
                                    action_type="auto_reply",
                                    decision="blocked",
                                    reason=f"Guard rejected: {guard.reason}",
                                    proposed_text=generated_text,
                                    status="blocked",
                                ))

                await session.commit()

            except Exception as e:
                await session.rollback()
                logger.error(f"Error processing pipeline event: {e}", exc_info=True)
                circuit_breaker.record_error(str(e))

message_pipeline = MessagePipeline()
