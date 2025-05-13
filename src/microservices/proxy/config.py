# Файл: ./src/microservices/proxy/config.py
import os

class Config:
    PORT = int(os.getenv('PORT', 8000))
    MONOLITH_URL = os.getenv('MONOLITH_URL', 'http://monolith:8080')
    MOVIES_SERVICE_URL = os.getenv('MOVIES_SERVICE_URL', 'http://movies-service:8081')
    EVENTS_SERVICE_URL = os.getenv('EVENTS_SERVICE_URL', 'http://events-service:8082')

    # Feature Flag для постепенной миграции
    GRADUAL_MIGRATION = os.getenv('GRADUAL_MIGRATION', 'false').lower() == 'true'

    # Процент запросов, перенаправляемых на микросервис фильмов
    try:
        MOVIES_MIGRATION_PERCENT = int(os.getenv('MOVIES_MIGRATION_PERCENT', '0'))
    except ValueError:
        MOVIES_MIGRATION_PERCENT = 0

    # Корректировка процента миграции
    if MOVIES_MIGRATION_PERCENT < 0:
        MOVIES_MIGRATION_PERCENT = 0
    elif MOVIES_MIGRATION_PERCENT > 100:
        MOVIES_MIGRATION_PERCENT = 100