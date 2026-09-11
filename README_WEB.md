# 🌍 Weather Analytics Dashboard + Browser Extension

Полное решение для мониторинга погоды и парсинга веб-страниц.

## 📁 Структура проекта

```
/workspace
├── web_server/           # FastAPI сервер
│   └── main.py          # Основной код сервера
├── templates/           # HTML шаблоны
│   └── index.html       # Веб-интерфейс дашборда
└── browser_extension/   # Браузерное расширение
    ├── manifest.json    # Конфигурация расширения
    ├── popup.html       # UI-popup расширения
    ├── popup.js         # Логика popup
    ├── content.js       # Контент-скрипт
    ├── background.js    # Service worker
    └── icons            # Иконки (placeholder)
```

## 🚀 Быстрый старт

### 1. Запуск веб-сервера

```bash
cd /workspace/web_server
python main.py
```

Сервер запустится на `http://localhost:8000`

**Что доступно:**
- `http://localhost:8000` - Веб-сайт с аналитикой погоды
- `http://localhost:8000/api/weather` - API погоды
- `http://localhost:8000/api/weather/history` - История запросов
- `http://localhost:8000/api/parse` - API для парсинга страниц
- `http://localhost:8000/api/health` - Проверка здоровья

### 2. Установка браузерного расширения

**Для Chrome/Edge/Brave:**

1. Откройте `chrome://extensions/`
2. Включите **"Режим разработчика"** (Developer mode) в правом верхнем углу
3. Нажмите **"Загрузить распакованное расширение"** (Load unpacked)
4. Выберите папку `/workspace/browser_extension`
5. Расширение установлено! ✓

**Использование:**
- Кликните на иконку расширения в панели браузера
- Введите URL или CSS селектор для парсинга
- Используйте контекстное меню (правый клик) для быстрого парсинга

## 🎯 Функционал

### Веб-сайт (Dashboard)
- 📊 **Аналитика погоды** в реальном времени
- 🌡️ **Температура** по 4 городам (Москва, Лондон, Нью-Йорк, Токио)
- 💨 **Влажность и ветер**
- 📈 **График изменений** температуры
- 📋 **История запросов**
- 🔄 **Автообновление** каждые 30 секунд

### Browser Extension
- 🔍 **Парсинг текущей страницы** с CSS селекторами
- 🌐 **Парсинг произвольных URL**
- 📋 **Копирование результатов** в буфер обмена
- 🌤️ **Быстрый доступ к погоде**
- 🖱️ **Контекстное меню** для выделенного текста

### API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/` | Веб-сайт дашборда |
| GET | `/api/weather` | Текущая погода + аналитика |
| GET | `/api/weather/history` | История всех запросов |
| POST | `/api/parse` | Парсинг страницы (JSON: `{url, selector}`) |
| GET | `/api/health` | Статус сервера |

## 📝 Примеры использования API

### Получить погоду
```bash
curl http://localhost:8000/api/weather
```

### Спарсить страницу
```bash
curl -X POST http://localhost:8000/api/parse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "selector": "h1"}'
```

### Python пример
```python
import requests

# Погода
response = requests.get('http://localhost:8000/api/weather')
data = response.json()
print(f"Средняя температура: {data['analytics']['avg_temperature']}°C")

# Парсинг
response = requests.post('http://localhost:8000/api/parse', json={
    'url': 'https://news.ycombinator.com',
    'selector': '.titleline a'
})
titles = response.json().get('selected_content', [])
print(f"Найдено заголовков: {len(titles)}")
```

## 🔧 Требования

```bash
pip install fastapi uvicorn requests beautifulsoup4 pandas plotly aiohttp python-multipart jinja2
```

## 🎨 Особенности

- ✅ **Асинхронная архитектура** - высокая производительность
- ✅ **Real-time обновления** - данные обновляются автоматически
- ✅ **Аналитика** - автоматический расчёт статистики
- ✅ **Красивый UI** - современный дизайн с градиентами
- ✅ **Расширяемость** - легко добавить новые города или функции
- ✅ **Плагин для браузера** - быстрый парсинг без открытия терминала

## ⚠️ Примечания

1. Сервер должен быть запущен для работы расширения
2. Для иконок расширения добавьте реальные PNG файлы (16x16, 48x48, 128x128)
3. Расширение работает только с `localhost:8000` по умолчанию
4. Для production используйте HTTPS и настройте CORS

## 📄 Лицензия

MIT License
