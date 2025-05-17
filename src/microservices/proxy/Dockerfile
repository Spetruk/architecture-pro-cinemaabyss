FROM python:3.9-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Определение переменных окружения по умолчанию
ENV PORT=8000
ENV MONOLITH_URL=http://monolith:8080
ENV MOVIES_SERVICE_URL=http://movies-service:8081
ENV EVENTS_SERVICE_URL=http://events-service:8082
ENV GRADUAL_MIGRATION=true
ENV MOVIES_MIGRATION_PERCENT=50

EXPOSE 8000

# Запуск приложения
CMD ["python", "app.py"]