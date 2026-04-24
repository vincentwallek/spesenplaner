"""
Budget Service — Kafka Producer.
Publishes payout-request events to Kafka for the payout-service to consume.
"""

import os
import json
import logging
from typing import Optional

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_PAYOUT_TOPIC", "payout-requests")

# Global producer reference
_producer: Optional[AIOKafkaProducer] = None


async def start_producer():
    """Initialize and start the Kafka producer."""
    global _producer
    try:
        _producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await _producer.start()
        logger.info(f"Kafka producer started, connected to {KAFKA_BOOTSTRAP_SERVERS}")
    except Exception as e:
        logger.warning(f"Could not start Kafka producer: {e}. Events will be skipped.")
        _producer = None


async def stop_producer():
    """Stop the Kafka producer gracefully."""
    global _producer
    if _producer:
        await _producer.stop()
        logger.info("Kafka producer stopped")
        _producer = None


async def publish_payout_event(
    expense_id: str,
    title: str,
    amount: float,
    currency: str,
) -> bool:
    """
    Publish a payout-request event to Kafka.
    The payout-service consumes these events asynchronously.

    Returns True if the event was published successfully.
    """
    if not _producer:
        logger.warning(f"Kafka producer not available. Skipping event for expense {expense_id}")
        return False

    event = {
        "event_type": "PAYOUT_REQUEST",
        "expense_id": expense_id,
        "title": title,
        "amount": amount,
        "currency": currency,
    }

    try:
        await _producer.send_and_wait(
            topic=KAFKA_TOPIC,
            key=expense_id,
            value=event,
        )
        logger.info(f"Published payout event for expense {expense_id} to topic '{KAFKA_TOPIC}'")
        return True
    except Exception as e:
        logger.error(f"Failed to publish Kafka event: {e}")
        return False
