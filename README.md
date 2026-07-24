# 🤖 FL Parser Bot — мониторинг фриланс-бирж

Telegram-бот, который непрерывно отслеживает новые задания на **Kwork**, **YouDo**
и **FL.ru** и присылает уведомления только о проектах, подходящих под ваши
фильтры (ключевые слова, стоп-слова, бюджет, биржи).

- Асинхронный (`asyncio`, `aiogram 3.x`, `aiohttp`, `SQLAlchemy 2.0 async`).
- Периодическая проверка по расписанию (`APScheduler`), интервал настраивается.
- Дедупликация: одно и то же задание не приходит дважды.
- Защита от блокировок: ротация User-Agent, случайные задержки, ретраи, таймауты, прокси.
- Гибкая фильтрация на стороне пользователя.

---

## 📂 Структура проекта

```
fl-parser/
├── main.py                  # Точка входа: бот + планировщик + БД
├── requirements.txt
├── .env.example             # Шаблон конфигурации
│
├── config/
│   └── settings.py          # Загрузка настроек из .env (python-dotenv)
│
├── database/
│   ├── models.py            # ORM-модели SQLAlchemy (User, Keyword, ...)
│   ├── engine.py            # Async-движок и фабрика сессий
│   └── repository.py        # Слой доступа к данным (все запросы к БД)
│
├── parsers/
│   ├── base.py              # Абстрактный BaseParser (+ safe_parse)
│   ├── dto.py               # Dataclass Project (единая модель задания)
│   ├── kwork.py             # Парсер Kwork  (JSON stateData)
│   ├── youdo.py             # Парсер YouDo  (JSON state / HTML)
│   ├── flru.py              # Парсер FL.ru  (HTML + BeautifulSoup)
│   └── __init__.py          # Реестр парсеров PARSER_REGISTRY
│
├── filters/
│   └── project_filter.py    # Чистая доменная логика фильтрации
│
├── services/
│   ├── monitoring.py        # Оркестратор цикла проверки
│   └── notifier.py          # Форматирование и отправка уведомлений
│
├── bot/
│   ├── bot.py               # Сборка Dispatcher, меню команд
│   ├── keyboards.py         # Инлайн-клавиатуры (выбор бирж)
│   └── handlers/
│       └── commands.py      # Обработчики всех команд
│
└── utils/
    ├── logger.py            # Настройка логирования (loguru)
    ├── http.py              # HTTP-клиент с ретраями/UA/прокси
    ├── user_agents.py       # Ротация User-Agent
    └── text.py              # Парсинг бюджета, обрезка описаний
```

**Архитектура (слои):** `parsers` (сбор данных) → `filters` (чистая логика) →
`services` (оркестрация) → `bot`/`database` (I/O). Парсеры не знают о фильтрах,
фильтры не знают о сети и БД — это упрощает тестирование и добавление новых бирж.

---

## 🚀 Установка

Требуется **Python 3.11+**.

```bash
# 1. Перейти в папку проекта
cd fl-parser

# 2. Создать виртуальное окружение
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. (опционально) Установить браузеры Playwright — только если USE_PLAYWRIGHT=true
playwright install chromium
```

---

## ⚙️ Настройка (`.env`)

Скопируйте шаблон и заполните значения:

```bash
cp .env.example .env
```

| Переменная | Описание | По умолчанию |
|---|---|---|
| `BOT_TOKEN` | Токен бота от [@BotFather](https://t.me/BotFather) | — (обязательно) |
| `CHECK_INTERVAL_MINUTES` | Интервал проверки бирж, мин | `5` |
| `REQUEST_DELAY_MIN` / `REQUEST_DELAY_MAX` | Диапазон случайной задержки между запросами, сек | `1.5` / `4.0` |
| `REQUEST_TIMEOUT` | Таймаут одного запроса, сек | `20` |
| `REQUEST_RETRIES` | Число повторных попыток | `3` |
| `DATABASE_URL` | Async-URL БД (SQLite/PostgreSQL) | `sqlite+aiosqlite:///./fl_parser.db` |
| `HTTP_PROXY` | HTTP-прокси `http://user:pass@host:port` | пусто |
| `LOG_LEVEL` | Уровень логов | `INFO` |
| `LOG_FILE` | Путь к файлу логов | `logs/bot.log` |
| `USE_PLAYWRIGHT` | Использовать headless-браузер для JS-сайтов | `false` |

### Как получить токен

1. Напишите [@BotFather](https://t.me/BotFather) команду `/newbot`.
2. Задайте имя и username бота.
3. Скопируйте выданный токен в `BOT_TOKEN`.

### PostgreSQL (опционально)

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/flparser
```
и `pip install asyncpg`.

---

## ▶️ Запуск

```bash
python main.py
```

При старте бот автоматически создаёт таблицы БД, регистрирует меню команд и
запускает планировщик. Логи пишутся в консоль и в `logs/bot.log` (с ротацией).

Остановка — `Ctrl+C`.

---

## 💬 Команды бота

| Команда | Назначение |
|---|---|
| `/start` | Регистрация пользователя |
| `/help` | Справка |
| `/settings` | Показать текущие настройки |
| `/keywords` | Ключевые слова (искать) |
| `/stopwords` | Стоп-слова (игнорировать) |
| `/budget` | Диапазон бюджета |
| `/sources` | Выбрать биржи (инлайн-кнопки) |
| `/status` | Статус мониторинга и время последней проверки |
| `/start_monitoring` | Включить уведомления (+ немедленная проверка) |
| `/stop_monitoring` | Выключить уведомления |

### Настройка фильтров

**Ключевые слова / стоп-слова** (можно списком через запятую):

```
/keywords add Python, Telegram, Django, FastAPI, AI, Парсер
/keywords del Django
/keywords clear
/keywords                 ← показать текущий список

/stopwords add WordPress, Photoshop, Дизайн, Логотип
```

**Бюджет:**

```
/budget 5000 50000        ← от 5000 до 50000
/budget 5000 -            ← только минимум
/budget clear             ← сбросить ограничения
```

**Биржи:** `/sources` — откроется клавиатура, где каждую биржу можно
включить (✅) / выключить (❌).

### Логика фильтрации

Задание проходит, если одновременно выполнено:

1. Биржа задания входит в выбранные пользователем.
2. В тексте **нет** ни одного стоп-слова.
3. Категория не входит в исключаемые.
4. Есть совпадение хотя бы по одному ключевому слову (если список не пуст).
5. Бюджет в диапазоне `[min, max]` (задания с нераспознанным «договорным»
   бюджетом не отсекаются — вы увидите их и решите сами).

### Формат уведомления

```
📌 Новое задание

🏷 Биржа: FL.ru
📝 Название: Разработать Telegram-бота
💰 Бюджет: 25 000 ₽
📂 Категория: Python
🕒 Опубликовано: 2 часа назад

Описание:
Первые 500 символов описания…

🔗 Открыть проект
```

---

## 🛡 Защита от блокировок

Реализовано в `utils/http.py` и настраивается через `.env`:

- **Случайные задержки** между запросами (`REQUEST_DELAY_MIN/MAX`).
- **Ротация User-Agent** на каждый запрос (`utils/user_agents.py`).
- **Повторные попытки** с экспоненциальной паузой (`REQUEST_RETRIES`).
- **Таймауты** (`REQUEST_TIMEOUT`).
- **HTTP-прокси** (`HTTP_PROXY`).
- **CAPTCHA/403/429**: фиксируются в логах, запрос повторяется. Для сайтов,
  требующих авторизацию или обход капчи (Kwork), рекомендуется прокси с
  авторизованными cookie или режим Playwright.

---

## 🧩 Парсинг: детали по биржам

| Биржа | Способ | Примечание |
|---|---|---|
| **FL.ru** | `aiohttp` + `BeautifulSoup` | Данные в HTML. Селекторы устойчивы к частичным изменениям. |
| **YouDo** | Встроенный JSON-стейт → HTML fallback | При активном JS включите `USE_PLAYWRIGHT`. |
| **Kwork** | JSON `window.stateData` | Биржа проектов требует авторизации — используйте прокси с cookie. |

> ⚠️ Верстка и API бирж периодически меняются. Парсеры написаны защищённо
> (`safe_parse` перехватывает любые ошибки и возвращает пустой список, не
> роняя цикл), но селекторы в `parsers/*.py` может потребоваться обновить.
> Добавить новую биржу = новый класс-наследник `BaseParser` + одна строка в
> `PARSER_REGISTRY` (`parsers/__init__.py`).

---

## 🗄 Хранение данных

SQLite по умолчанию (`fl_parser.db`). Хранятся: пользователи и их настройки,
ключевые/стоп-слова, бюджеты, подключённые биржи, отправленные задания (для
дедупликации), время последней проверки.

Таблицы создаются автоматически при запуске. Для продакшена и версионирования
схемы можно подключить **Alembic**:

```bash
pip install alembic
alembic init migrations
# в migrations/env.py указать: target_metadata = database.models.Base.metadata
alembic revision --autogenerate -m "init"
alembic upgrade head
```

---

## 📝 Логирование

`loguru`, вывод в консоль (цветной) и в файл с ротацией 10 МБ / хранением 14
дней. Логируются: запуск парсеров, найденные задания, отправленные сообщения,
ошибки сети/парсинга/Telegram API, время цикла.

---

## 🧪 Проверка логики без Telegram

Модули `filters` и `utils.text` — чистые (без I/O) и легко тестируются:

```python
from parsers.dto import Project
from filters.project_filter import FilterCriteria, ProjectFilter

f = ProjectFilter(FilterCriteria(keywords=["python"], stopwords=["wordpress"], min_budget=5000))
p = Project(title="Бот на Python", url="https://x/1", source="FL.ru", budget_value=20000)
assert f.matches(p)
```

---

## 🚢 Деплой на сервер

### Вариант 1 — Docker Compose (рекомендуется)

Нужен сервер (VPS) с установленными **Docker** и **Docker Compose**.

```bash
# 1. Скопировать проект на сервер (git clone / scp / rsync)
git clone <repo> fl-parser && cd fl-parser

# 2. Создать .env и указать токен
cp .env.example .env
nano .env                     # вписать BOT_TOKEN

# 3. Собрать и запустить в фоне
docker compose up -d --build

# 4. Логи и управление
docker compose logs -f bot    # смотреть логи
docker compose restart bot    # перезапуск
docker compose down           # остановить
```

- Данные БД и логи хранятся в named volumes (`bot-data`, `bot-logs`) и
  переживают пересборку контейнера.
- `restart: unless-stopped` — бот сам поднимется после падения или ребута
  сервера.
- Секреты (`.env`) **не** попадают в образ (исключены в `.dockerignore`),
  передаются в контейнер через `env_file`.
- Graceful shutdown: `tini` как PID 1 корректно доставляет `SIGTERM` от
  `docker stop` в aiogram.

**Обновление до новой версии:**
```bash
git pull
docker compose up -d --build
```

**PostgreSQL вместо SQLite:** раскомментируйте сервис `db` и блок
`environment` с `DATABASE_URL` в `docker-compose.yml`, добавьте `asyncpg` в
`requirements.txt` и пересоберите.

### Вариант 2 — systemd (без Docker)

Готовый юнит — `deploy/fl-parser-bot.service` (инструкция в шапке файла):

```bash
sudo cp deploy/fl-parser-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fl-parser-bot
sudo journalctl -u fl-parser-bot -f
```

`Restart=always` перезапускает бота при сбоях; `enable` — автозапуск при
загрузке сервера.

### Чек-лист перед продакшеном

- [ ] Создан `.env` с реальным `BOT_TOKEN` (файл не коммитить — он в `.gitignore`).
- [ ] Настроен `CHECK_INTERVAL_MINUTES` (слишком частые проверки → риск блокировки).
- [ ] При необходимости указан `HTTP_PROXY` (особенно для Kwork).
- [ ] Проверены логи первого цикла: `docker compose logs -f bot`.
- [ ] Настроено резервное копирование volume `bot-data` (если важна история).

---

## ⚖️ Дисклеймер

Парсинг должен соответствовать правилам и `robots.txt` бирж. Проект
предназначен для личного использования и образовательных целей. Соблюдайте
разумные интервалы запросов, чтобы не создавать нагрузку на сайты.
