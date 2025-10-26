# Используем официальный образ Python
FROM python:3.9-slim-buster

# Устанавливаем системные зависимости для Playwright
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libxkbcommon-x11-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm-dev \
    libasound2 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY requirements.txt .
COPY main.py .
COPY .env .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем браузеры Playwright
RUN playwright install --with-deps chromium

# Команда для запуска приложения
CMD ["python", "main.py"]

# Открываем порт для Flask API
EXPOSE 5000