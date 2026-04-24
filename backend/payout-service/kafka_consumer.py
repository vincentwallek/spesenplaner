"""
Payout Service — Kafka Consumer.
Consumes payout-request events from Kafka and processes payouts.
"""

import os
import json
import asyncio
import logging

from aiokafka import AIOKafkaConsumer
from database import async_session
from crud import process_payout

import httpx

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_PAYOUT_TOPIC", "payout-requests")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "payout-service-group")
REQUEST_SERVICE_URL = os.getenv("REQUEST_SERVICE_URL", "http://localhost:3001")


async def _notify_request_service(expense_id: str, status: str):
    """Callback to request-service to update expense status after payout."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.put(
                f"{REQUEST_SERVICE_URL}/expenses/{expense_id}/status",
                json={"status": status},
            )
            logger.info(f"Notified request-service: expense {expense_id} -> {status}")
    except Exception as e:
        logger.warning(f"Failed to notify request-service: {e}")


async def consume_payout_events():
    """
    Background task: Continuously consume payout-request events from Kafka.
    For each event, process the payout and notify request-service.
    """
    consumer = None
    while True:
        try:
            consumer = AIOKafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=KAFKA_GROUP_ID,
                value_deserializer=lambda x: json.loads(x.decode("utf-8")),
                auto_offset_reset="earliest",
            )
            await consumer.start()
            logger.info(
                f"Kafka consumer started. Listening on topic '{KAFKA_TOPIC}' "
                f"(group: {KAFKA_GROUP_ID})"
            )

            async for msg in consumer:
                event = msg.value
                logger.info(f"Received Kafka event: {event}")

                if event.get("event_type") != "PAYOUT_REQUEST":
                    logger.warning(f"Unknown event type: {event.get('event_type')}")
                    continue

                expense_id = event.get("expense_id")
                if not expense_id:
                    logger.warning("Event missing expense_id, skipping")
                    continue

                try:
                    async with async_session() as session:
                        record = await process_payout(
                            session=session,
                            expense_id=expense_id,
                            title=event.get("title", ""),
                            amount=event.get("amount", 0.0),
                            currency=event.get("currency", "EUR"),
                        )

                    # Notify request-service of the payout result
                    await _notify_request_service(expense_id, record.status)
                    logger.info(
                        f"Payout processed for expense {expense_id}: {record.status}"
                    )

                except Exception as e:
                    logger.error(f"Error processing payout for {expense_id}: {e}")

        except asyncio.CancelledError:
            logger.info("Kafka consumer task cancelled")
            break
        except Exception as e:
            logger.warning(f"Kafka consumer error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)
        finally:
            if consumer:
                try:
                    await consumer.stop()
                except Exception:
                    pass
