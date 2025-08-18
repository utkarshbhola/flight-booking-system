# kafka_consumer.py
import asyncio
from aiokafka import AIOKafkaConsumer
import json

async def consume():
    consumer = AIOKafkaConsumer(
        "bookings",
        bootstrap_servers="localhost:9092",
        group_id="booking_service",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    await consumer.start()
    try:
        async for msg in consumer:
            print("📩 Received:", msg.value)
            # You can trigger email, SMS, analytics update, etc.
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume())
