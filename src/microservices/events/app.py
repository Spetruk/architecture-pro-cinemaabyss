# app.py
import json
import os
import time
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import threading
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Получение настроек из переменных окружения
PORT = os.getenv('PORT', '8082')
KAFKA_BROKERS = os.getenv('KAFKA_BROKERS', 'kafka:9092')

# Инициализация Kafka-продюсера
producer = None
consumer_threads = []

class Event:
    def __init__(self, event_type, payload):
        self.id = str(uuid.uuid4())
        self.type = event_type
        self.timestamp = datetime.now().isoformat()
        self.payload = payload

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp,
            "payload": self.payload
        }

def init_kafka_producer():
    global producer
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKERS],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            api_version=(2, 7, 0)
        )
        logger.info("Kafka producer initialized successfully")
    except Exception as e:
        logger.error(f"Failed to create Kafka producer: {e}")
        producer = None

def consume_messages(topic):
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=[KAFKA_BROKERS],
            auto_offset_reset='latest',
            enable_auto_commit=True,
            group_id=f'events-service-{topic}',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            api_version=(2, 7, 0)
        )

        logger.info(f"Started consuming messages from topic: {topic}")

        for message in consumer:
            logger.info(f"Received message from topic {topic}: {message.value}")
            process_message(topic, message.value)

    except Exception as e:
        logger.error(f"Error in consumer for topic {topic}: {e}")

def process_message(topic, message):
    try:
        # Обработка сообщения в зависимости от топика
        if topic == "movie-events":
            logger.info(f"Processing movie event: {message}")
        elif topic == "user-events":
            logger.info(f"Processing user event: {message}")
        elif topic == "payment-events":
            logger.info(f"Processing payment event: {message}")
    except Exception as e:
        logger.error(f"Error processing message from topic {topic}: {e}")

def send_to_kafka(topic, event):
    if producer is None:
        return {"error": "Kafka producer not available"}, 500

    try:
        future = producer.send(topic, value=event.to_dict())
        record_metadata = future.get(timeout=10)

        logger.info(f"Event sent to topic {topic}, partition {record_metadata.partition}, offset {record_metadata.offset}")

        return {
            "status": "success",
            "partition": record_metadata.partition,
            "offset": record_metadata.offset,
            "event": event.to_dict()
        }, 201
    except KafkaError as e:
        logger.error(f"Error sending message to Kafka: {e}")
        return {"error": f"Failed to send message to Kafka: {str(e)}"}, 500

@app.route('/health', methods=['GET'])
@app.route('/api/events/health', methods=['GET'])
def handle_health():
    return jsonify({"status": True})

@app.route('/api/events/movie', methods=['POST'])
def handle_movie_event():
    if not request.json:
        return jsonify({"error": "Invalid request format"}), 400

    movie_event = request.json

    # Создаем событие
    event_id = f"movie-{movie_event.get('movie_id', '')}-{movie_event.get('action', '')}"
    event = Event("movie", movie_event)
    event.id = event_id

    # Отправляем событие в Kafka
    result, status_code = send_to_kafka("movie-events", event)
    return jsonify(result), status_code

@app.route('/api/events/user', methods=['POST'])
def handle_user_event():
    if not request.json:
        return jsonify({"error": "Invalid request format"}), 400

    user_event = request.json

    # Создаем событие
    event_id = f"user-{user_event.get('user_id', '')}-{user_event.get('action', '')}"
    event = Event("user", user_event)
    event.id = event_id

    # Отправляем событие в Kafka
    result, status_code = send_to_kafka("user-events", event)
    return jsonify(result), status_code

@app.route('/api/events/payment', methods=['POST'])
def handle_payment_event():
    if not request.json:
        return jsonify({"error": "Invalid request format"}), 400

    payment_event = request.json

    # Создаем событие
    event_id = f"payment-{payment_event.get('payment_id', '')}-{payment_event.get('status', '')}"
    event = Event("payment", payment_event)
    event.id = event_id

    # Отправляем событие в Kafka
    result, status_code = send_to_kafka("payment-events", event)
    return jsonify(result), status_code

def start_consumers():
    # Запуск потребителей Kafka в отдельных потоках
    topics = ["movie-events", "user-events", "payment-events"]

    for topic in topics:
        consumer_thread = threading.Thread(target=consume_messages, args=(topic,))
        consumer_thread.daemon = True
        consumer_thread.start()
        consumer_threads.append(consumer_thread)
        logger.info(f"Started consumer thread for topic: {topic}")

if __name__ == '__main__':
    # Инициализация Kafka-продюсера
    init_kafka_producer()

    # Запуск потребителей Kafka
    start_consumers()

    # Запуск Flask-сервера
    logger.info(f"Starting events service on port {PORT}")
    app.run(host='0.0.0.0', port=int(PORT), debug=False)