"""Kafka producer and consumer base classes"""

import json
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Callable

from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka.serialization import SerializationContext, MessageField

from app.core.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KafkaProducer:
    """Kafka async producer for publishing messages"""

    def __init__(self):
        """Initialize Kafka producer"""
        self._producer: Producer | None = None
        self._is_connected: bool = False

    def connect(self) -> None:
        """Initialize Kafka producer connection"""
        if self._is_connected:
            logger.warning("kafka_producer_already_connected")
            return

        try:
            config = {
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "client.id": settings.KAFKA_CLIENT_ID,
            }

            self._producer = Producer(config)
            self._is_connected = True
            logger.info(
                "kafka_producer_connected",
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            )
        except Exception as e:
            logger.error(
                "kafka_producer_connection_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def disconnect(self) -> None:
        """Close Kafka producer connection"""
        if not self._is_connected:
            return

        try:
            if self._producer:
                # Flush any pending messages
                self._producer.flush(timeout=10)
            self._is_connected = False
            logger.info("kafka_producer_disconnected")
        except Exception as e:
            logger.error(
                "kafka_producer_disconnect_failed",
                error=str(e),
                error_type=type(e).__name__,
            )

    async def produce(
        self,
        topic: str,
        value: dict[str, Any] | str,
        key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        Produce a message to a Kafka topic.

        Args:
            topic: Topic name
            value: Message value (dict will be JSON serialized)
            key: Optional message key
            headers: Optional message headers
        """
        if not self._producer:
            raise RuntimeError("Producer not connected. Call connect() first.")

        # Serialize value
        if isinstance(value, dict):
            serialized_value = json.dumps(value).encode("utf-8")
        else:
            serialized_value = value.encode("utf-8") if isinstance(value, str) else value

        # Serialize key
        serialized_key = key.encode("utf-8") if key else None

        # Prepare headers
        kafka_headers = []
        if headers:
            kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]

        try:
            # Produce message (async callback)
            self._producer.produce(
                topic,
                value=serialized_value,
                key=serialized_key,
                headers=kafka_headers,
                callback=self._delivery_callback,
            )

            # Trigger delivery callbacks
            self._producer.poll(0)

            logger.debug(
                "kafka_message_produced",
                topic=topic,
                key=key,
                has_headers=bool(headers),
            )
        except KafkaException as e:
            logger.error(
                "kafka_produce_failed",
                topic=topic,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def _delivery_callback(self, err: KafkaError | None, msg: Any) -> None:
        """Callback for message delivery confirmation"""
        if err:
            logger.error(
                "kafka_message_delivery_failed",
                error=str(err),
                topic=msg.topic() if msg else None,
            )
        else:
            logger.debug(
                "kafka_message_delivered",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
            )

    def flush(self, timeout: float = 10.0) -> None:
        """
        Flush pending messages.

        Args:
            timeout: Maximum time to wait for messages to be delivered
        """
        if self._producer:
            self._producer.flush(timeout=timeout)


class KafkaConsumer:
    """Kafka async consumer for consuming messages"""

    def __init__(self, group_id: str | None = None):
        """
        Initialize Kafka consumer.

        Args:
            group_id: Consumer group ID (uses default from settings if None)
        """
        self._consumer: Consumer | None = None
        self._group_id = group_id or settings.KAFKA_GROUP_ID
        self._is_connected: bool = False

    def connect(self, topics: list[str]) -> None:
        """
        Initialize Kafka consumer and subscribe to topics.

        Args:
            topics: List of topic names to subscribe to
        """
        if self._is_connected:
            logger.warning("kafka_consumer_already_connected")
            return

        try:
            config = {
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "group.id": self._group_id,
                "auto.offset.reset": settings.KAFKA_AUTO_OFFSET_RESET,
                "enable.auto.commit": settings.KAFKA_ENABLE_AUTO_COMMIT,
            }

            self._consumer = Consumer(config)
            self._consumer.subscribe(topics)

            self._is_connected = True
            logger.info(
                "kafka_consumer_connected",
                group_id=self._group_id,
                topics=topics,
            )
        except Exception as e:
            logger.error(
                "kafka_consumer_connection_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def disconnect(self) -> None:
        """Close Kafka consumer connection"""
        if not self._is_connected:
            return

        try:
            if self._consumer:
                self._consumer.close()
            self._is_connected = False
            logger.info("kafka_consumer_disconnected")
        except Exception as e:
            logger.error(
                "kafka_consumer_disconnect_failed",
                error=str(e),
                error_type=type(e).__name__,
            )

    async def consume(
        self, timeout: float = 1.0
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Consume messages from subscribed topics.

        Args:
            timeout: Poll timeout in seconds

        Yields:
            Message dictionaries with 'topic', 'key', 'value', 'headers', 'partition', 'offset'
        """
        if not self._consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")

        while self._is_connected:
            try:
                msg = self._consumer.poll(timeout=timeout)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition - continue
                        continue
                    else:
                        logger.error(
                            "kafka_consumer_error",
                            error=str(msg.error()),
                            code=msg.error().code(),
                        )
                        continue

                # Parse message
                try:
                    value = json.loads(msg.value().decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # If not JSON, return as string
                    value = msg.value().decode("utf-8")

                key = msg.key().decode("utf-8") if msg.key() else None

                # Parse headers
                headers = {}
                if msg.headers():
                    headers = {k: v.decode("utf-8") for k, v in msg.headers()}

                message = {
                    "topic": msg.topic(),
                    "partition": msg.partition(),
                    "offset": msg.offset(),
                    "key": key,
                    "value": value,
                    "headers": headers,
                    "timestamp": msg.timestamp(),
                }

                yield message

            except Exception as e:
                logger.error(
                    "kafka_consume_error",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                # Continue consuming despite errors
                continue

    def commit(self) -> None:
        """Manually commit current offsets"""
        if self._consumer:
            self._consumer.commit()


class KafkaAdmin:
    """Kafka admin client for topic management"""

    def __init__(self):
        """Initialize Kafka admin client"""
        self._admin: AdminClient | None = None

    def connect(self) -> None:
        """Initialize Kafka admin client"""
        config = {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
        }
        self._admin = AdminClient(config)

    async def create_topic(
        self,
        topic_name: str,
        num_partitions: int = 3,
        replication_factor: int = 1,
    ) -> None:
        """
        Create a Kafka topic.

        Args:
            topic_name: Topic name
            num_partitions: Number of partitions
            replication_factor: Replication factor
        """
        if not self._admin:
            self.connect()

        topic = NewTopic(
            topic_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
        )

        futures = self._admin.create_topics([topic])

        for topic_name, future in futures.items():
            try:
                future.result()  # Wait for topic creation
                logger.info("kafka_topic_created", topic=topic_name)
            except Exception as e:
                logger.error(
                    "kafka_topic_creation_failed",
                    topic=topic_name,
                    error=str(e),
                )
                raise


# Global instances
_kafka_producer: KafkaProducer | None = None
_kafka_consumers: dict[str, KafkaConsumer] = {}


def get_kafka_producer() -> KafkaProducer:
    """Get or create global Kafka producer"""
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = KafkaProducer()
        _kafka_producer.connect()
    return _kafka_producer


def get_kafka_consumer(group_id: str | None = None) -> KafkaConsumer:
    """Get or create Kafka consumer for a group"""
    global _kafka_consumers
    gid = group_id or settings.KAFKA_GROUP_ID
    if gid not in _kafka_consumers:
        _kafka_consumers[gid] = KafkaConsumer(group_id=gid)
    return _kafka_consumers[gid]


async def close_kafka() -> None:
    """Close all Kafka connections"""
    global _kafka_producer, _kafka_consumers

    if _kafka_producer:
        _kafka_producer.disconnect()
        _kafka_producer = None

    for consumer in _kafka_consumers.values():
        consumer.disconnect()
    _kafka_consumers.clear()
