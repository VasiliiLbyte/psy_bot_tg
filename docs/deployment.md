 Развертывание

## Локальный запуск
1. Клонировать репозиторий.
2. Создать виртуальное окружение: `python -m venv venv`
3. Активировать: `source venv/bin/activate` (Linux/Mac) или `venv\Scripts\activate` (Windows)
4. Установить зависимости: `pip install -r requirements.txt`
5. Создать `.env` с переменными:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENROUTER_API_KEY`
   - (опционально) `MODEL_SYMPTOM_COLLECTION`, `MODEL_EVALUATION`, `MODEL_RECOMMENDATIONS`
6. Запустить: `python main.py`

## Docker (опционально)
- Использовать образ `python:3.11-slim`.
- Скопировать код, установить зависимости.
- Смонтировать том для `data/`.
- Пример `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
Продакшн

Использовать systemd или supervisor для автоматического перезапуска.
Настроить логирование в файл.
Регулярное бэкапирование data/.