import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from backend.app.db.models import Rule, Contact, Chat

class RuleDecision(BaseModel):
    analysis_allowed: bool = True
    auto_reply_allowed: bool = False
    summary_allowed: bool = True
    requires_draft_approval: bool = True
    min_importance_for_summary: int = 7
    assigned_profile: Optional[str] = "default"
    matched_rule: Optional[str] = None
    reason: str = "Default policy"

class RuleEngine:
    """
    Deterministic rule engine that decides what actions are permitted
    prior to any AI invocation (Section 4).
    """

    @classmethod
    def evaluate(
        cls,
        sender_id: str,
        chat_id: str,
        chat_type: str,
        contact: Optional[Contact] = None,
        chat: Optional[Chat] = None,
        rules: Optional[List[Rule]] = None,
        current_time: Optional[datetime.datetime] = None,
    ) -> RuleDecision:
        now = current_time or datetime.datetime.utcnow()

        # Priority 1: Contact blacklist
        if contact and contact.is_blacklisted:
            return RuleDecision(
                analysis_allowed=False,
                auto_reply_allowed=False,
                summary_allowed=False,
                requires_draft_approval=False,
                matched_rule="contact_blacklist",
                reason=f"Contact {sender_id} is explicitly blacklisted",
            )

        # Priority 2: Chat disabled
        if chat and not chat.enabled:
            return RuleDecision(
                analysis_allowed=False,
                auto_reply_allowed=False,
                summary_allowed=False,
                requires_draft_approval=False,
                matched_rule="chat_disabled",
                reason=f"Chat {chat_id} is disabled",
            )

        # Priority 3: Channels are read-only (summary only, never reply)
        if chat_type == "channel":
            return RuleDecision(
                analysis_allowed=True,
                auto_reply_allowed=False,
                summary_allowed=True,
                requires_draft_approval=False,
                min_importance_for_summary=8,
                matched_rule="channel_safety",
                reason="Telegram channels never receive replies",
            )

        # Priority 4: User-specific DB Rules (highest rule priority)
        active_rules = sorted(
            [r for r in (rules or []) if r.is_active],
            key=lambda r: r.priority,
        )
        user_rules = [r for r in active_rules if r.scope == "user" and r.subject == f"user:{sender_id}"]
        if user_rules:
            rule = user_rules[0]
            cond = rule.conditions or {}
            auto_reply = cond.get("auto_reply", False)
            return RuleDecision(
                analysis_allowed=cond.get("analysis", True),
                auto_reply_allowed=auto_reply,
                summary_allowed=cond.get("summary", True),
                requires_draft_approval=not auto_reply or cond.get("require_draft_approval", False),
                min_importance_for_summary=cond.get("min_importance", 7),
                matched_rule=f"rule:{rule.id} ({rule.name})",
                reason=f"Сработало персональное правило '{rule.name}' для пользователя {sender_id}",
            )

        # Priority 5: Contact Card manual override (if user explicitly set mode on card, not 'inherit')
        if contact and contact.ai_mode and contact.ai_mode not in ["inherit", "default"]:
            if contact.ai_mode == "ignored":
                return RuleDecision(
                    analysis_allowed=False,
                    auto_reply_allowed=False,
                    summary_allowed=False,
                    requires_draft_approval=False,
                    matched_rule="contact_override:ignored",
                    reason=f"Ручная настройка на карточке {contact.display_name}: Игнорировать",
                )
            elif contact.ai_mode == "analysis_only":
                return RuleDecision(
                    analysis_allowed=True,
                    auto_reply_allowed=False,
                    summary_allowed=True,
                    requires_draft_approval=False,
                    min_importance_for_summary=7,
                    matched_rule="contact_override:analysis_only",
                    reason=f"Ручная настройка на карточке {contact.display_name}: Только анализ",
                )
            elif contact.ai_mode == "draft":
                return RuleDecision(
                    analysis_allowed=True,
                    auto_reply_allowed=False,
                    summary_allowed=True,
                    requires_draft_approval=True,
                    min_importance_for_summary=7,
                    matched_rule="contact_override:draft",
                    reason=f"Ручная настройка на карточке {contact.display_name}: Черновик (согласование)",
                )
            elif contact.ai_mode == "auto_reply":
                return RuleDecision(
                    analysis_allowed=True,
                    auto_reply_allowed=True,
                    summary_allowed=True,
                    requires_draft_approval=False,
                    min_importance_for_summary=7,
                    matched_rule="contact_override:auto_reply",
                    reason=f"Ручная настройка на карточке {contact.display_name}: Всегда автоответ",
                )

        # Priority 6: Category, Group, Chat Type, and Global Rules from DB
        category_rules = [r for r in active_rules if r.scope != "user"]
        for rule in category_rules:
            cond = rule.conditions or {}
            matched = False

            if rule.scope == "global":
                matched = True
            elif rule.scope in ["all_groups", "group"]:
                if not rule.subject or rule.subject in ["all", "group:all", "type:group", "all_groups"]:
                    matched = (chat_type in ["group", "supergroup"])
                elif rule.subject in [f"chat:{chat_id}", f"group:{chat_id}", str(chat_id)]:
                    matched = True
            elif rule.scope == "chat_type":
                if rule.subject in [f"type:{chat_type}", chat_type]:
                    matched = True
                elif rule.subject in ["type:group", "group"] and chat_type in ["group", "supergroup"]:
                    matched = True
                elif rule.subject in ["type:private", "private"] and chat_type == "private":
                    matched = True
            elif rule.scope == "category" and contact and rule.subject in [f"category:{contact.category}", contact.category]:
                matched = True

            if matched:
                quiet_start = cond.get("quiet_hours_start")
                quiet_end = cond.get("quiet_hours_end")
                if quiet_start is not None and quiet_end is not None:
                    hour = now.hour
                    is_quiet = hour >= quiet_start or hour < quiet_end if quiet_start > quiet_end else quiet_start <= hour < quiet_end
                    auto_reply = False if (is_quiet and cond.get("quiet_hours_disable_auto_reply", True)) else cond.get("auto_reply", False)
                else:
                    auto_reply = cond.get("auto_reply", False)

                analysis = cond.get("analysis", True)
                summary = cond.get("summary", True)
                min_imp = cond.get("min_importance", 7)
                profile = cond.get("profile", "default")
                req_draft = not auto_reply or cond.get("require_draft_approval", False)

                return RuleDecision(
                    analysis_allowed=analysis,
                    auto_reply_allowed=auto_reply,
                    summary_allowed=summary,
                    requires_draft_approval=req_draft,
                    min_importance_for_summary=min_imp,
                    assigned_profile=profile,
                    matched_rule=f"rule:{rule.id} ({rule.name})",
                    reason=f"Сработало правило категории '{rule.name}'",
                )

        # Priority 7: Default Category Fallback (for close / family)
        if contact and contact.category in ["close", "family"]:
            return RuleDecision(
                analysis_allowed=True,
                auto_reply_allowed=True,
                summary_allowed=True,
                requires_draft_approval=False,
                min_importance_for_summary=7,
                matched_rule=f"category_default:{contact.category}",
                reason=f"Категория '{contact.category}' по умолчанию имеет включенный автоответ",
            )

        # Default fallback for unknown senders / strangers (Section 4.1):
        return RuleDecision(
            analysis_allowed=True,
            auto_reply_allowed=False,
            summary_allowed=True,
            requires_draft_approval=True,
            min_importance_for_summary=8,
            assigned_profile="default",
            matched_rule="default_stranger_policy",
            reason="Стандартная политика для новых контактов: черновик, без автоответа",
        )
