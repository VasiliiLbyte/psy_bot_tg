# Правила разработки

## Стиль кода
- Следовать PEP 8.
- Использовать type hints для всех функций.
- Имена переменных и функций в snake_case.
- Классы в CamelCase.
- Константы в UPPER_CASE.

## Структура проекта
neuro_bot/
├── .env
├── .cursorrules
├── main.py
├── db.py
├── handlers/
│ ├── init.py
│ ├── commands.py
│ ├── callbacks.py
│ └── messages.py
├── states.py
├── storage.py
├── storage_json_legacy.py
├── context_manager.py
├── openrouter_client.py
├── model_router.py
├── parser.py
├── models.py
├── safety.py
├── utils.py
├── utils_tg.py
├── data/
│ ├── bot.db
│ └── incidents.json
├── tests/
│ ├── test_storage.py
│ ├── test_parser.py
│ └── ...
├── docs/
│ └── ...
└── requirements.txt

text

## Модульность
- Каждый модуль отвечает за одну зону ответственности.
- Импорты: сначала стандартные библиотеки, затем сторонние, затем свои.

## Обработка ошибок
- Использовать try/except с логированием.
- Внешние API должны иметь retry и fallback.

## Асинхронность
- Все операции ввода-вывода (Telegram, HTTP, файлы) должны быть асинхронными.
- Для файловых операций использовать aiofiles или асинхронные обертки.

## Логирование
- Использовать стандартный модуль logging.
- Уровни: DEBUG, INFO, WARNING, ERROR.
- Логировать ошибки, но не чувствительные данные.

## Безопасность
- Не хранить токены в коде.
- Использовать .env для секретов.
- Добавлять дисклеймеры во все ответы с рекомендациями.
- При экстренных фразах немедленно отправлять предупреждение и предлагать завершить.