## Тестирование

Запуск всех тестов:

```bash
python -m pytest -q
```

Ключевые тесты:
- `tests/test_db.py`: конкурентные записи (проверка отсутствия race condition).
- `tests/test_openrouter_client.py`: мок HTTP для OpenRouter клиента.
- `tests/test_utils_tg.py`: корректная отмена keep-typing задач.
