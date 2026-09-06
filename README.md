# Personal Telegram AI Assistant

Персональный AI-ассистент для личного Telegram-аккаунта на базе MTProto API (Telethon), детерминированного Rule Engine, структурированного AI Analyzer, фильтра безопасности Response Guard и веб-интерфейса на React + Vite.

---

## 🚀 Быстрый старт (Локальный запуск)

### 1. Запуск Backend (FastAPI + Async Worker + SQLite)

```bash
# Активация виртуального окружения
source backend/.venv/bin/activate

# Запуск сервера API и фонового воркера
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

* API Docs (Swagger): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* Healthcheck: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Запуск Frontend (React + TypeScript + Vite)

```bash
cd frontend
npm run dev
```

* Веб-интерфейс доступен по адресу: [http://localhost:5173](http://localhost:5173)

---

## 🧪 Запуск автоматических тестов

```bash
PYTHONPATH=. ./backend/.venv/bin/pytest backend/tests -v
```

Тестовый набор проверяет:
- Приоритеты Rule Engine (черные списки, каналы, правила пользователей, категории).
- Фильтры безопасности Response Guard (запрет бот-команд, шелл-инъекций, утечек ключей и токенов).
- AI Analyzer (структурированная JSON-схема, извлечение задач, определение срочности и спама).
- Сквозной пайплайн обработки сообщений с записью в базу и отправкой алертов в «Избранное».

---

## 🛠 Подключение реального Telegram (когда будут api_id и api_hash)

1. Откройте веб-интерфейс [http://localhost:5173](http://localhost:5173) и перейдите во вкладку **«Настройки & MTProto»** (или используйте файл `.env`).
2. Введите ваши `api_id` и `api_hash`, полученные на [my.telegram.org](https://my.telegram.org).
3. Введите номер телефона и нажмите **«Запросить код подтверждения»**.
4. Введите полученный в приложении Telegram 5-значный код (и 2FA-пароль, если он включен).
5. Сессия будет зашифрована локально через Fernet (AES-128-CBC) и сохранена в БД.

До получения API-ключей система работает в полнофункциональном режиме **Telegram Sandbox Simulator**!
