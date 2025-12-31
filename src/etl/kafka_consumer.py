import json
import os
import time
from datetime import datetime
from kafka import KafkaConsumer
import clickhouse_connect
from src.utils.logger import logger

# Configurations
KAFKA_TOPIC = "interactions"
KAFKA_BOOTSTRAP = "kafka:9092"
CH_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")

def get_clickhouse_client():
    while True:
        try:
            client = clickhouse_connect.get_client(host=CH_HOST, port=8123)
            return client
        except Exception as e:
            logger.warning(f"Waiting for ClickHouse... {e}")
            time.sleep(5)

def main():
    logger.info("Starting Kafka Consumer...")
    
    ch_client = get_clickhouse_client()
    logger.info("Connected to ClickHouse.")
    
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='clickhouse_loader',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        logger.info(f"Subscribed to topic: {KAFKA_TOPIC}")
    except Exception as e:
        logger.error(f"Failed to connect to Kafka: {e}")
        return

    # Main Loop
    for message in consumer:
        try:
            event = message.value
            logger.info(f"Received event: {event}")
            
            # user_id UInt32, movie_id UInt32, rating UInt8, timestamp DateTime
            data = [[
                event['user_id'],
                event['movie_id'],
                event['rating'],
                datetime.strptime(event['timestamp'], '%Y-%m-%d %H:%M:%S'),
            ]]
            
            ch_client.insert('interactions', data, column_names=['user_id', 'movie_id', 'rating', 'timestamp'])
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")

if __name__ == "__main__":
    main()
