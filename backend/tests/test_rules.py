import pytest
from backend.app.rules.engine import RuleEngine, RuleDecision
from backend.app.db.models import Rule, Contact, Chat

def test_blacklisted_contact_blocked():
    contact = Contact(
        telegram_user_id="bad_user",
        display_name="Bad User",
        is_blacklisted=True,
    )
    decision = RuleEngine.evaluate(
        sender_id="bad_user",
        chat_id="chat_1",
        chat_type="private",
        contact=contact,
    )
    assert not decision.analysis_allowed
    assert not decision.auto_reply_allowed
    assert not decision.summary_allowed
    assert decision.matched_rule == "contact_blacklist"

def test_disabled_chat_blocked():
    chat = Chat(
        telegram_chat_id="chat_disabled",
        enabled=False,
    )
    decision = RuleEngine.evaluate(
        sender_id="user_1",
        chat_id="chat_disabled",
        chat_type="group",
        chat=chat,
    )
    assert not decision.analysis_allowed
    assert not decision.auto_reply_allowed
    assert decision.matched_rule == "chat_disabled"

def test_channel_never_replies():
    decision = RuleEngine.evaluate(
        sender_id="channel_bot",
        chat_id="channel_123",
        chat_type="channel",
    )
    assert decision.analysis_allowed
    assert not decision.auto_reply_allowed
    assert decision.summary_allowed
    assert decision.matched_rule == "channel_safety"

def test_stranger_safe_default():
    decision = RuleEngine.evaluate(
        sender_id="stranger_404",
        chat_id="chat_stranger",
        chat_type="private",
        contact=None,
    )
    assert decision.analysis_allowed
    assert not decision.auto_reply_allowed
    assert decision.requires_draft_approval
    assert decision.min_importance_for_summary == 8
    assert decision.matched_rule == "default_stranger_policy"

def test_rule_priority_order():
    rule_high = Rule(
        id=1,
        name="Allow Ivan",
        scope="user",
        subject="user:ivan",
        action="allow_auto",
        priority=10,
        conditions={"auto_reply": True, "analysis": True, "min_importance": 6},
        is_active=True,
    )
    rule_low = Rule(
        id=2,
        name="Ban Group",
        scope="group",
        subject="chat:dev_group",
        action="ignore",
        priority=50,
        conditions={"auto_reply": False, "analysis": False},
        is_active=True,
    )
    # Even if in dev_group, Ivan rule has higher priority (10 < 50)
    decision = RuleEngine.evaluate(
        sender_id="ivan",
        chat_id="dev_group",
        chat_type="group",
        rules=[rule_low, rule_high],
    )
    assert decision.auto_reply_allowed is True
    assert decision.analysis_allowed is True
    assert "rule:1" in decision.matched_rule

def test_category_rule_evaluation():
    contact_close = Contact(
        telegram_user_id="mom_123",
        display_name="Мама",
        category="close",
    )
    rule_close = Rule(
        id=10,
        name="Auto-reply for close category",
        scope="category",
        subject="category:close",
        action="allow_auto",
        priority=20,
        conditions={"auto_reply": True, "analysis": True, "min_importance": 5},
        is_active=True,
    )
    decision = RuleEngine.evaluate(
        sender_id="mom_123",
        chat_id="chat_mom",
        chat_type="private",
        contact=contact_close,
        rules=[rule_close],
    )
    assert decision.auto_reply_allowed is True
    assert decision.requires_draft_approval is False
    assert decision.min_importance_for_summary == 5
    assert "rule:10" in decision.matched_rule

def test_all_groups_rule_evaluation():
    rule_all_groups = Rule(
        id=15,
        name="All Groups Force Draft",
        scope="chat_type",
        subject="type:group",
        action="force_draft",
        priority=30,
        conditions={"auto_reply": False, "analysis": True, "min_importance": 7},
        is_active=True,
    )
    decision = RuleEngine.evaluate(
        sender_id="colleague_99",
        chat_id="-100987654321",
        chat_type="group",
        rules=[rule_all_groups],
    )
    assert decision.analysis_allowed is True
    assert decision.auto_reply_allowed is False
    assert decision.requires_draft_approval is True
    assert "rule:15" in decision.matched_rule
