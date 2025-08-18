from aiokafka import AIOKafkaProducer
import asyncio
import json

producer = None

async def get_kafka_producer():
    global producer
    if producer is None:
        producer = AIOKafkaProducer(
            bootstrap_servers="localhost:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        await producer.start()
    return producer

async def send_kafka_message(topic: str, message: dict):
    producer = await get_kafka_producer()
    await producer.send_and_wait(topic, message)
