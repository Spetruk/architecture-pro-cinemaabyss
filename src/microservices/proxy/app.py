# Файл: ./src/microservices/proxy/app.py
import random
import logging
import requests
from flask import Flask, request, Response, jsonify
from urllib.parse import urljoin, quote
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Загрузка конфигурации из переменных окружения
PORT = int(os.getenv('PORT', 8000))
MONOLITH_URL = os.getenv('MONOLITH_URL', 'http://monolith:8080')
MOVIES_SERVICE_URL = os.getenv('MOVIES_SERVICE_URL', 'http://movies-service:8081')
EVENTS_SERVICE_URL = os.getenv('EVENTS_SERVICE_URL', 'http://events-service:8082')
GRADUAL_MIGRATION = os.getenv('GRADUAL_MIGRATION', 'false').lower() == 'true'

try:
    MOVIES_MIGRATION_PERCENT = int(os.getenv('MOVIES_MIGRATION_PERCENT', '0'))
except ValueError:
    MOVIES_MIGRATION_PERCENT = 0

# Обеспечиваем, что процент миграции находится в пределах 0-100
MOVIES_MIGRATION_PERCENT = max(0, min(MOVIES_MIGRATION_PERCENT, 100))

# Вывод информации о конфигурации
logger.info(f"Starting proxy service on port {PORT}")
logger.info(f"Monolith URL: {MONOLITH_URL}")
logger.info(f"Movies Service URL: {MOVIES_SERVICE_URL}")
logger.info(f"Events Service URL: {EVENTS_SERVICE_URL}")

logger.info(f"Gradual Migration: {GRADUAL_MIGRATION}")
logger.info(f"Movies Migration Percent: {MOVIES_MIGRATION_PERCENT}%")

def forward_request(target_url, path=None, strip_api_prefix=False):
    """
    Перенаправляет запрос на указанный URL

    Args:
        target_url: URL целевого сервиса
        path: Путь запроса (если None, используется оригинальный)
        strip_api_prefix: Удалять ли префикс /api из пути
    """
    # Получение пути и метода запроса
    request_path = path if path is not None else request.path
    request_method = request.method


    # Убедимся, что путь начинается с "/"
    if not request_path.startswith('/'):
        request_path = '/' + request_path

    # Удаляем префикс /api если нужно
    if strip_api_prefix and request_path.startswith('/api'):
        request_path = request_path[4:]  # Удаляем '/api'
        logger.info(f"Stripped /api prefix, new path: {request_path}")

    # Формирование полного URL для запроса
    url = urljoin(target_url, request_path)

    # Добавление query параметров, если они есть
    if request.query_string:
        url = f"{url}?{request.query_string.decode('utf-8')}"

    # Логирование перенаправления
    logger.info(f"Forwarding {request_method} request to: {url}")
    logger.info(f"Request data: {request.get_data()}")
    logger.info(f"Request content type: {request.content_type}")

    try:
        # Формирование и отправка запроса
        headers = {key: value for (key, value) in request.headers if key != 'Host'}

        # Отправка запроса
        resp = requests.request(
            method=request_method,
            url=url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=10  # Добавлен таймаут для предотвращения зависания
        )

        logger.info(f"Received response from {url}: {resp.status_code}")

        # Формирование и возврат ответа
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.headers.items()
                   if name.lower() not in excluded_headers]

        return Response(resp.content, resp.status_code, headers)

    except requests.RequestException as e:
        logger.error(f"Error forwarding request to {url}: {e}")
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy(path):
    """
    Обрабатывает все входящие запросы и перенаправляет их на соответствующие сервисы
    """
    full_path = f"/{path}" if path else "/"
    logger.info(f"Received request: {request.method} {full_path}")

    # Тестовый endpoint для проверки работоспособности прокси
    if full_path == '/health':
        return jsonify({"status": "ok", "service": "proxy"}), 200

    # Обработка запросов к API фильмов с постепенной миграцией
    if full_path.startswith('/api/movies'):
        # Если включена постепенная миграция, используем случайное распределение
        if GRADUAL_MIGRATION and random.randint(1, 100) <= MOVIES_MIGRATION_PERCENT:
            logger.info(f"Routing to movies service: {full_path}")
            return forward_request(MOVIES_SERVICE_URL, full_path, strip_api_prefix=True)
        else:
            logger.info(f"Routing to monolith: {full_path}")
            return forward_request(MONOLITH_URL, full_path)

    # Запросы к сервису событий всегда направляются на микросервис
    elif full_path.startswith('/api/events'):
        logger.info(f"Routing to events service: {full_path}")
        return forward_request(EVENTS_SERVICE_URL, full_path, strip_api_prefix=True)

    # Все остальные запросы направляются на монолит
    else:
        logger.info(f"Routing to monolith: {full_path}")
        return forward_request(MONOLITH_URL, full_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)