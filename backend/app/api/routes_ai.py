import json
import logging
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.config import settings, DATA_DIR
from backend.app.ai.analyzer import AIAnalyzer

from backend.app.config import settings, DATA_DIR, load_ai_config_override

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

class AiConfigRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = "gemini-3.8-flash"
    gemini_proxy: Optional[str] = None
    provider: Optional[str] = "gemini"

class AiTestRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    gemini_proxy: Optional[str] = None

@router.get("/config")
async def get_ai_config():
    load_ai_config_override(settings)
    key = settings.GEMINI_API_KEY
    masked = ""
    if key:
        masked = f"{key[:7]}...{key[-4:]}" if len(key) > 12 else "***"

    return {
        "provider": settings.AI_PROVIDER,
        "gemini_model": settings.GEMINI_MODEL or "gemini-3.8-flash",
        "gemini_proxy": settings.GEMINI_PROXY or "",
        "has_gemini_key": bool(key),
        "gemini_key_masked": masked,
        "available_models": [
            {"id": "gemini-3.8-flash", "name": "Gemini 3.8 Flash (Новейшая быстрая модель Google 2026)"},
            {"id": "gemini-3.6-flash", "name": "Gemini 3.6 Flash (Стабильная модель)"},
            {"id": "gemini-3.5-flash", "name": "Gemini 3.5 Flash (Проверенная надежная модель)"},
            {"id": "gemini-flash-latest", "name": "Gemini Flash (Latest)"},
            {"id": "gemini-flash-lite-latest", "name": "Gemini Flash-Lite (Latest)"},
        ],
    }

@router.post("/config")
async def save_ai_config(req: AiConfigRequest):
    if req.gemini_api_key is not None:
        settings.GEMINI_API_KEY = req.gemini_api_key.strip()
    if req.gemini_model:
        settings.GEMINI_MODEL = req.gemini_model.strip()
    if req.gemini_proxy is not None:
        settings.GEMINI_PROXY = req.gemini_proxy.strip()
    if req.provider:
        settings.AI_PROVIDER = req.provider.strip()

    # Persist to disk
    ai_file = DATA_DIR / "ai_config.json"
    data = {
        "gemini_api_key": settings.GEMINI_API_KEY,
        "gemini_model": settings.GEMINI_MODEL,
        "gemini_proxy": settings.GEMINI_PROXY,
        "provider": settings.AI_PROVIDER,
    }
    with open(ai_file, "w") as f:
        json.dump(data, f)

    return {
        "success": True,
        "message": "Настройки AI успешно сохранены",
        "has_gemini_key": bool(settings.GEMINI_API_KEY),
        "gemini_model": settings.GEMINI_MODEL,
        "gemini_proxy": settings.GEMINI_PROXY,
        "provider": settings.AI_PROVIDER,
    }

@router.post("/test")
async def test_ai_connection(req: AiTestRequest):
    import httpx
    load_ai_config_override(settings)
    test_key = req.gemini_api_key.strip() if req.gemini_api_key else settings.GEMINI_API_KEY
    if not test_key:
        return {"success": False, "error": "Gemini API ключ не указан"}

    primary_model = req.gemini_model.strip() if req.gemini_model else (settings.GEMINI_MODEL or "gemini-3.5-flash")
    test_proxy = req.gemini_proxy.strip() if req.gemini_proxy is not None else settings.GEMINI_PROXY

    fallback_model = "gemini-3.5-flash" if primary_model != "gemini-3.5-flash" else "gemini-flash-latest"
    models_to_try = [primary_model]
    if fallback_model not in models_to_try:
        models_to_try.append(fallback_model)

    client_kwargs: dict = {"timeout": 20.0}
    if test_proxy:
        client_kwargs["proxy"] = test_proxy

    last_error = ""

    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            for idx, model in enumerate(models_to_try):
                gen_config = {
                    "responseMimeType": "application/json",
                    "temperature": 0.1,
                }
                if "3.6" not in model and "flash-latest" not in model:
                    gen_config["thinkingConfig"] = {"thinkingBudget": 0}

                body = {
                    "systemInstruction": {
                        "parts": [{"text": "You are an AI assistant. Return valid JSON with intent, importance (1-10), and summary."}]
                    },
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": "Привет! Завтра в 10:00 релиз, нужно проверить деплой."}]
                        }
                    ],
                    "generationConfig": gen_config,
                }

                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={test_key}"
                try:
                    resp = await client.post(url, json=body)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        import re
                        if raw_text.startswith("```"):
                            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                            raw_text = re.sub(r"\s*```$", "", raw_text)
                        parsed = json.loads(raw_text)
                        warning_note = None
                        if idx > 0:
                            warning_note = f"Основная выбранная модель '{primary_model}' временно недоступна или перегружена ({last_error}), но резервная модель '{model}' ответила штатно!"
                        return {
                            "success": True,
                            "model": model,
                            "analysis": parsed,
                            "warning": warning_note,
                        }
                    elif resp.status_code in [503, 429, 404]:
                        try:
                            err_body = resp.json()
                            msg = err_body.get("error", {}).get("message", f"HTTP {resp.status_code}")
                        except Exception:
                            msg = f"HTTP {resp.status_code}"
                        last_error = f"HTTP {resp.status_code} ({msg})"
                        logger.warning(f"test_ai_connection: {model} -> {last_error}, пробуем резервную модель...")
                        continue
                    else:
                        try:
                            err_body = resp.json()
                            err_msg = err_body.get("error", {}).get("message", f"HTTP {resp.status_code}")
                        except Exception:
                            err_msg = f"HTTP {resp.status_code}: {resp.text}"
                        return {"success": False, "error": f"Ошибка Gemini API ({resp.status_code}): {err_msg}"}
                except (httpx.ConnectTimeout, httpx.ReadTimeout) as timeout_err:
                    last_error = f"Таймаут ожидания ответа от модели {model} (20s)"
                    logger.warning(f"test_ai_connection: {last_error}, пробуем резервную модель...")
                    continue

        return {
            "success": False,
            "error": f"Не удалось получить ответ от моделей Gemini. Последняя ошибка: {last_error}. Проверьте доступность Google API или смените модель.",
        }

    except httpx.ProxyError as e:
        err_msg = str(e) or repr(e)
        return {
            "success": False,
            "error": f"Ошибка подключения к прокси ({test_proxy}): {err_msg}. Проверьте правильность адреса и запущен ли ваш локальный прокси.",
        }
    except httpx.ConnectError as e:
        err_msg = str(e) or repr(e)
        return {
            "success": False,
            "error": f"Ошибка сетевого соединения с Google Gemini API ({err_msg}). Доступ к generativelanguage.googleapis.com заблокирован провайдером или отсутствует интернет. Включите VPN или укажите HTTP/SOCKS5 Прокси в настройках ниже.",
        }
    except httpx.TimeoutException as e:
        return {
            "success": False,
            "error": "Превышено общее время ожидания сетевого запроса к Google API (30 сек). Проверьте интернет-соединение, VPN или настройки прокси.",
        }
    except Exception as e:
        err_detail = str(e) if str(e).strip() else f"{type(e).__name__}: {repr(e)}"
        return {"success": False, "error": f"Ошибка сети / запроса ({type(e).__name__}): {err_detail}"}
