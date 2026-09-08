FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для Playwright
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка Python-зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Установка браузеров Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Копирование кода приложения
COPY *.py ./
COPY data/ ./data/

# Создание директории для результатов краулинга
RUN mkdir -p /app/data/pages

# Переменные окружения по умолчанию
ENV PARSER_HEADLESS=true \
    PARSER_BROWSER_TYPE=chromium

# Точка входа
CMD ["python", "main.py"]
