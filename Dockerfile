# ============================================================
#  FL Parser Bot — production image
# ============================================================
FROM python:3.12-slim AS base

# Оптимизации Python и pip для контейнера.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=UTC

WORKDIR /app

# 1. Зависимости ставим отдельным слоем — кэшируется, пока не менялся requirements.txt.
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2. Код приложения.
COPY . .

# 3. Непривилегированный пользователь + каталоги для данных и логов.
#    Named volumes при первом создании наследуют владельца этих каталогов.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data /app/logs \
    && chown -R appuser:appuser /app
USER appuser

# Значения по умолчанию для контейнера (переопределяются через env_file/environment).
ENV DATABASE_URL="sqlite+aiosqlite:////app/data/fl_parser.db" \
    LOG_FILE="/app/logs/bot.log"

# aiogram сам обрабатывает SIGTERM/SIGINT → graceful shutdown по `docker stop`.
# Для reaping дочерних процессов запускайте с init:
#   compose — init: true (см. docker-compose.yml); docker run — флаг --init.
CMD ["python", "main.py"]
