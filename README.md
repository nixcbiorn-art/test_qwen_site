# Парсер и монитор

## Статус проекта
✅ **Все тесты пройдены:** 33/33 (100% success rate)  
🚀 **Архитектура:** Гибридная система (Python бэкенд + WPF фронтенд)  
📦 **Контейнеризация:** Docker и docker-compose готовы к использованию  
🔔 **Уведомления:** Email, Webhook, Telegram каналы  
⚡ **Асинхронность:** Полная поддержка async/await для параллельного мониторинга  
💻 **EXE файл:** Готовый исполняемый файл для запуска без установки Python  

## Возможности

### Основные функции
- **Мониторинг API** с детектированием изменений в данных
- **Гибкая авторизация**: Bearer Token, API Key, браузерный логин через Playwright
- **Пагинация**: Автоматическое определение типа (page/offset), обход всех страниц
- **Маппинг полей**: Нормализация данных из разных источников через вложенные пути
- **Детектирование изменений**: Сравнение снапшотов с определением добавленных, удалённых и изменённых записей
- **Хранение данных**: SQLite с версионированием снапшотов и историей изменений
- **Превью для LLM**: Компактная выжимка структуры API для дешёвой проверки маппинга нейросетями
- **CLI инструменты**: Управление настройками, превью эндпоинтов, импорт маппинга от LLM
- **WPF приложение**: Графический интерфейс для настройки и управления мониторингом
- **Лаунчер**: Системный трей с быстрым стартом/остановкой мониторинга (сборка в EXE)

### Уведомления (Notifier)
Модульная система оповещений о найденных изменениях:
- **EmailNotifier**: SMTP с HTML-шаблонами и вложениями
- **WebhookNotifier**: POST-запросы с retry-логикой
- **TelegramNotifier**: Интеграция с Telegram Bot API
- **CompositeNotifier**: Рассылка по нескольким каналам одновременно

### Асинхронный режим
Для высоконагруженных сценариев доступна полная async-версия:
- `async_api_client.py` — HTTP-клиент на aiohttp с retry и экспоненциальной задержкой
- `async_storage.py` — асинхронная работа с SQLite через aiosqlite
- `async_monitor.py` — параллельный опрос всех эндпоинтов через `asyncio.gather()`
- Неблокирующие I/O операции (сеть, БД)
- Полная совместимость API с синхронной версией

### Логирование и валидация
- **Structlog**: Структурированное машиночитаемое логирование для интеграции с ELK/Grafana Loki
- **Pydantic**: Валидация конфигурации при старте, авто-коррекция значений, типизация всех настроек
- **Конфигурация**: Поддержка .env переменных окружения и JSON файлов

## Установка

### Через pip (локально)
```bash
pip install -r requirements.txt
playwright install
```

### Через Docker
```bash
docker-compose up -d
```

## Настройка

### Переменные окружения (.env)
Создайте файл `.env` в корне проекта:
```env
# API Configuration
API_BASE_URL=https://api.example.com/v1
SITE_URL=https://example.com
REQUEST_TIMEOUT=30
MAX_RETRIES=3

# Auth
USERNAME=user@example.com
PASSWORD=secret_password

# Monitoring
CHECK_INTERVAL_SECONDS=300
HEADLESS_BROWSER=true

# Database
DATABASE_PATH=data/changes.db

# Notifications
NOTIFICATION_ENABLED=true
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER=alert@example.com
EMAIL_PASSWORD=app_password
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=-1001234567890
WEBHOOK_URL=https://hooks.slack.com/services/...
```

### Через UI (рекомендуется)
Вкладка "Настройки" в WPF-приложении (ParserApp):
- Выбор скрипта (Monitor/Crawler)
- Site URL, API Base URL
- Логин/пароль для авторизации
- Интервал проверки
- Headless-режим браузера
- Редактируемый список API-эндпоинтов

Для каждого endpoint'а выбирается **способ взаимодействия**:
- **none** — без авторизации (публичные API)
- **token** — статический токен для этого endpoint'а
- **login** — общий токен через браузерный логин (Username/Password)

Кнопка "Сохранить настройки" пишет `data/settings.json`, который `config.py` подхватывает автоматически.

### Вручную (если не используешь GUI)
1. `config.py` — дефолтные URL, логин, пароль, список `API_ENDPOINTS`
2. `auth.py` — селекторы формы авторизации (если логин через браузер)
3. `data/settings.json` — формат:
```json
{
  "site_url": "https://example.com",
  "api_base_url": "https://api.example.com/v1",
  "username": "",
  "password": "",
  "check_interval_seconds": 300,
  "headless_browser": true,
  "selected_script": "monitor",
  "endpoints": [
    {"path": "/data/public-feed", "auth_mode": "none"},
    {"path": "/data/status", "auth_mode": "token", "token": "my-static-token"},
    {"path": "/data/items", "auth_mode": "login"}
  ]
}
```

#### Пагинация — обход ВСЕХ страниц источника
По умолчанию парсер делает один запрос. Чтобы обойти все страницы:
```json
{"path": "/estate/x?page[size]=50&page[number]=1", "auth_mode": "token",
 "token": "...", "paginate": true, "max_pages": 100}
```
Тип пагинации определяется автоматически по параметрам в `path`:
- `page[number]` или `page` — постраничная
- `offset` — по смещению

#### Маппинг — нормализация полей между источниками
```json
{"path": "/estate/x", "auth_mode": "token", "token": "...",
 "items_path": "data",
 "mapping": {
   "id": "id",
   "title": "attributes.name",
   "price": "attributes.price.value"
 }}
```
- `items_path` — где в ответе лежит список элементов
- `mapping` — `{\"выходное_поле\": \"путь.в.json"}` для одного элемента

Если каждый элемент содержит поле `id`, детектор показывает конкретно: какая запись добавилась, пропала, и в каком поле изменилось значение.

#### Превью для LLM — дешёвая проверка полей
```bash
python preview_endpoint.py          # список эндпоинтов с номерами
python preview_endpoint.py 0        # превью эндпоинта №0 в консоль
python preview_endpoint.py 0 --rows 50 --out preview.json
```
Инструмент готовит компактную выжимку (`approx_keys` + первые N строк) для отправки в LLM.

#### Импорт готового маппинга от нейросети
**Через CLI:**
```bash
python apply_mapping.py                        # список эндпоинтов
python apply_mapping.py 0 llm_mapping.json      # применить к эндпоинту №0
python apply_mapping.py 0 llm_mapping.json --paginate
```

**Формат `llm_mapping.json`:**
```json
{
  "items_path": "data",
  "mapping": {"id": "id", "title": "attributes.name", "price": "attributes.price.value"}
}
```

**Важно про безопасность:** Пароль и токены хранятся в `settings.json` в открытом виде. Это локальный dev-инструмент — не размещай файл в публичных репозиториях.

## Запуск

### 🖥️ Готовый EXE-файл (рекомендуется)
Собранный исполняемый файл находится в папке `dist/MarketMonitor`.

**Linux:**
```bash
./dist/MarketMonitor
```

**Windows:**
```bash
dist\MarketMonitor.exe
```

Приложение запустится в фоновом режиме:
- С GUI: иконка в системном трее с меню Start/Stop/Exit
- Без GUI: консольный режим с логированием в `logs/monitor.log`

Подробная инструкция по сборке и использованию: [BUILD_EXE.md](BUILD_EXE.md)

### Синхронный режим (классический)
```bash
python main.py
```

### Асинхронный режим (высокая производительность)
```bash
python async_monitor.py
```

### Полный обход сайта (crawler)
```bash
python crawler.py
```
Обходит сайт по внутренним ссылкам (BFS), сохраняет HTML в `data/pages/` и метаданные в SQLite.

### Тестирование
```bash
pytest
```

## Скрипты (папка scripts/)
- `scripts/setup-python.bat` — установка pip-зависимостей и браузеров Playwright
- `scripts/install-dotnet-sdk.ps1` — проверка и установка .NET 8 SDK
- `scripts/run-parser-app.ps1` — restore + build + run для ParserApp (WPF)

Запуск PowerShell-скриптов:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
cd C:\parser\scripts
.\install-dotnet-sdk.ps1
.\run-parser-app.ps1
```

## Структура проекта

### Python модули
| Файл | Описание |
|------|----------|
| `config.py` | Конфигурация через Pydantic, .env и JSON |
| `auth.py` | Авторизация (Bearer, API Key, браузерный логин) |
| `api_client.py` | Синхронный HTTP-клиент с retry-логикой |
| `async_api_client.py` | Асинхронный HTTP-клиент на aiohttp |
| `scraper.py` | Парсинг HTML через Playwright |
| `crawler.py` | BFS обход всего сайта |
| `storage.py` | Синхронная работа с SQLite |
| `async_storage.py` | Асинхронная работа с SQLite (aiosqlite) |
| `detector.py` | Алгоритмы сравнения снапшотов |
| `mapping.py` | Маппинг полей с поддержкой вложенных путей |
| `paginator.py` | Обработка различных типов пагинации |
| `monitor.py` | Синхронный цикл мониторинга |
| `async_monitor.py` | Асинхронный мониторинг с параллельным опросом |
| `notifier.py` | Система уведомлений (Email, Webhook, Telegram) |
| `preview.py` / `preview_endpoint.py` | Превью данных для LLM |
| `apply_mapping.py` | CLI для импорта маппинга от LLM |
| `launcher.py` | 💻 Лаунчер с системным треем для запуска в фоне |
| `main.py` | Точка входа (синхронная версия) |
| `finance_connector.py` | 📈 Финансовый коннектор: получение котировок OHLCV, стаканы заявок |
| `technical_analyzer.py` | 📊 Технический анализ: индикаторы SMA, RSI, MACD |

### WPF приложение (ParserApp/)
| Компонент | Назначение |
|-----------|------------|
| `MainWindow.xaml/.cs` | Главный экран управления |
| `MappingDialog.xaml/.cs` | Диалог настройки маппинга |
| `Models/` | Модели данных (EndpointConfig, MappingRule) |
| `Services/` | Сервисы работы с API и файлами |

### Инфраструктура
| Файл | Описание |
|------|----------|
| `Dockerfile` | Образ Python приложения |
| `docker-compose.yml` | Оркестрация контейнеров |
| `requirements.txt` | Зависимости Python (aiohttp, structlog, pydantic, pystray, Pillow) |
| `pytest.ini` | Конфигурация тестов |
| `.env.example` | Шаблон переменных окружения |
| `BUILD_EXE.md` | 📦 Инструкция по сборке EXE-файла через PyInstaller |
| `launcher.py` | 💻 Исходный код лаунчера с системным треем |

### Данные
| Путь | Описание |
|------|----------|
| `data/settings.json` | Активные настройки мониторинга |
| `data/changes.db` | SQLite база снапшотов и истории изменений |
| `data/pages/` | HTML-дампы страниц (после crawler.py) |

### Тесты
| Файл | coverage |
|------|----------|
| `tests/test_api_client.py` | Тесты HTTP-клиента и авторизации |
| `tests/test_detector.py` | Тесты алгоритмов детектирования |
| `tests/test_mapping.py` | Тесты маппинга полей |

## Ограничения текущей версии
- Не проверяет `robots.txt` и `Crawl-delay` (для crawler.py)
- Не отличает контентные дубли (пагинация, сортировки, utm-метки)
- Не резюмирует прерванный обход — повторный запуск crawler начинает с нуля
- Не рендерит контент, подгружаемый позже `networkidle` (бесконечный скролл)

## Архитектурные преимущества
✅ **Модульность**: Каждый компонент независим и тестируем  
✅ **Масштабируемость**: Async-режим для параллельной обработки сотен эндпоинтов  
✅ **Надёжность**: Retry-логика, валидация конфигов, структурированное логирование  
✅ **Гибкость**: Поддержка разных типов авторизации, пагинации и структур API  
✅ **DevOps-ready**: Docker, CI/ready структура, env-конфигурация  
✅ **Расширяемость**: Интерфейсы для новых каналов уведомлений, стратегий авторизации  
✅ **Финансовые инструменты**: 📈 Интеграция с рынком акций, технические индикаторы, торговые сигналы  
✅ **Визуализация**: 📊 Интерактивные дашборды Plotly с темной темой
