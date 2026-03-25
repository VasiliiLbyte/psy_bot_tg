# Cursor rules for NeuroDiagnostic Telegram Bot

# Импорт внешних правил
import:
  - docs/project-plan.md
  - docs/architecture.md
  - docs/tech-stack.md
  - docs/development-guidelines.md
  - docs/testing.md
  - docs/deployment.md
  - docs/context-management.md

# Глобальные настройки
language: python
python_version: "3.11"
project_type: telegram_bot

# Автоматические действия
auto_format: true
auto_lint: true
auto_test_on_save: false

# Основные правила
- Всегда следуй плану проекта (project-plan.md).
- При разработке новых модулей учитывай архитектуру из architecture.md.
- Используй соглашения из development-guidelines.md.
- Перед началом работы ознакомься с context-management.md для понимания хранения контекста.