# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Определение переменных окружения по умолчанию
ENV PORT=8082
ENV KAFKA_BROKERS=kafka:9092

# Порт для приложения
EXPOSE 8082

# Команда запуска
CMD ["python", "app.py"]