# Технологический стек

## Язык и окружение
- Python 3.11+
- Virtualenv / venv

## Основные библиотеки
- aiogram==3.x (асинхронный фреймворк для Telegram ботов)
- httpx (асинхронный HTTP клиент для OpenRouter)
- pydantic (валидация данных)
- tiktoken (подсчёт токенов)
- python-dotenv (переменные окружения)
- aiosqlite (SQLite-хранилище)

## Опционально
- pytest (тестирование)
- pytest-asyncio (асинхронные тесты)
- docker (контейнеризация)

## API
- Telegram Bot API (через aiogram)
- OpenRouter API (универсальный доступ к LLM)

## Хранение
- SQLite (для MVP)
- В перспективе: PostgreSQL