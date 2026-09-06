import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.config import DATA_DIR

logger = logging.getLogger(__name__)

CATEGORIES_FILE = DATA_DIR / "categories.json"

DEFAULT_CATEGORIES: List[Dict[str, Any]] = [
    {
        "id": "close",
        "name": "Близкий",
        "color": "#f43f5e",
        "icon": "Heart",
        "description": "Семья, любимый человек, самые близкие люди",
        "prompt_instruction": (
            "Собеседник — очень близкий человек или член семьи. "
            "Тон: теплый, заботливый, искренний, неформальный, исключительно на 'ты'. "
            "Отвечай просто и естественно, как реальный человек отвечает близким в Telegram. "
            "Категорически запрещен любой официоз, канцелярские фразы и роботизированные шаблоны. "
            "Если спрашивают, как дела или зовут встретиться — отвечай по-доброму и прямо."
        ),
        "is_custom": False,
    },
    {
        "id": "family",
        "name": "Семья",
        "color": "#f97316",
        "icon": "Home",
        "description": "Родители, дети, родственники",
        "prompt_instruction": (
            "Собеседник — член семьи (родители/дети/родственники). "
            "Тон: родной, внимательный, теплый, заботливый, на 'ты'. "
            "Отвечай кратко, по-домашнему, без формальностей."
        ),
        "is_custom": False,
    },
    {
        "id": "friend",
        "name": "Друг",
        "color": "#10b981",
        "icon": "Smile",
        "description": "Друзья, хорошие знакомые, приятели",
        "prompt_instruction": (
            "Собеседник — хороший друг или приятель. "
            "Тон: дружеский, легкий, живой, на 'ты', допустим дружеский юмор. "
            "Отвечай непринужденно, кратко и по существу диалога."
        ),
        "is_custom": False,
    },
    {
        "id": "colleague",
        "name": "Коллега",
        "color": "#38bdf8",
        "icon": "Briefcase",
        "description": "Коллеги по работе, соавторы, подрядчики",
        "prompt_instruction": (
            "Собеседник — коллега по работе или рабочий партнер. "
            "Тон: конструктивный, деловой, доброжелательный, на 'ты' или на 'Вы' в зависимости от контекста. "
            "Фокус на задачах, сроках, ясности и договоренностях."
        ),
        "is_custom": False,
    },
    {
        "id": "client",
        "name": "Клиент",
        "color": "#a855f7",
        "icon": "UserCheck",
        "description": "Клиенты, заказчики, покупатели",
        "prompt_instruction": (
            "Собеседник — клиент или заказчик. "
            "Тон: уважительный, вежливый, клиентоориентированный, строго на 'Вы'. "
            "Высокая готовность помочь, четкость, аккуратность и профессионализм."
        ),
        "is_custom": False,
    },
    {
        "id": "vip",
        "name": "VIP",
        "color": "#eab308",
        "icon": "Star",
        "description": "Руководство, ключевые партнеры, инвесторы",
        "prompt_instruction": (
            "Собеседник — VIP персона или руководство. "
            "Тон: максимально внимательный, оперативный, уважительный, тактичный и точный."
        ),
        "is_custom": False,
    },
    {
        "id": "stranger",
        "name": "Незнакомец",
        "color": "#94a3b8",
        "icon": "HelpCircle",
        "description": "Неизвестные контакты, новые входящие",
        "prompt_instruction": (
            "Собеседник — незнакомый или малознакомый контакт. "
            "Тон: сдержанный, нейтральный, вежливый, на 'Вы'. "
            "Категорически запрещено делиться личной информацией, паролями, планами, контактами других людей."
        ),
        "is_custom": False,
    },
]

class CategoriesService:
    @classmethod
    def _load_all(cls) -> List[Dict[str, Any]]:
        if not CATEGORIES_FILE.exists():
            cls._save_all(DEFAULT_CATEGORIES)
            return DEFAULT_CATEGORIES

        try:
            with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
                categories = json.load(f)
                # Ensure default categories exist
                existing_ids = {c["id"] for c in categories}
                updated = False
                for default_cat in DEFAULT_CATEGORIES:
                    if default_cat["id"] not in existing_ids:
                        categories.append(default_cat)
                        updated = True
                if updated:
                    cls._save_all(categories)
                return categories
        except Exception as e:
            logger.error(f"Failed to read categories.json: {e}")
            return DEFAULT_CATEGORIES

    @classmethod
    def _save_all(cls, categories: List[Dict[str, Any]]) -> None:
        try:
            with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
                json.dump(categories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save categories.json: {e}")

    @classmethod
    def get_categories(cls) -> List[Dict[str, Any]]:
        return cls._load_all()

    @classmethod
    def get_category(cls, cat_id: str) -> Optional[Dict[str, Any]]:
        cats = cls._load_all()
        for c in cats:
            if c["id"] == cat_id:
                return c
        return None

    @classmethod
    def save_category(
        cls,
        cat_id: str,
        name: str,
        color: str = "#38bdf8",
        icon: str = "Tag",
        description: str = "",
        prompt_instruction: str = "",
    ) -> Dict[str, Any]:
        cats = cls._load_all()
        cat_id = cat_id.strip().lower()
        for i, c in enumerate(cats):
            if c["id"] == cat_id:
                # Update existing
                cats[i]["name"] = name
                cats[i]["color"] = color
                cats[i]["description"] = description
                cats[i]["prompt_instruction"] = prompt_instruction
                cls._save_all(cats)
                return cats[i]

        # New category
        new_cat = {
            "id": cat_id,
            "name": name,
            "color": color,
            "icon": icon,
            "description": description,
            "prompt_instruction": prompt_instruction,
            "is_custom": True,
        }
        cats.append(new_cat)
        cls._save_all(cats)
        return new_cat

    @classmethod
    def delete_category(cls, cat_id: str) -> bool:
        cats = cls._load_all()
        # Cannot delete non-custom default categories
        filtered = [c for c in cats if not (c["id"] == cat_id and c.get("is_custom", False))]
        if len(filtered) < len(cats):
            cls._save_all(filtered)
            return True
        return False
