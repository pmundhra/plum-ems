"""Kafka producer and consumer implementation"""

import asyncio
import atexit
import json
import signal
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Dict, Type

from confluent_kafka import Consumer, Producer, KafkaException, Message

from app.core.settings import settings
from app.utils.logger import get_logger

from app.core.base.handlers import MessageHandlerFactory, MessageHandler, InterimOutput

logger = get_logger(__name__)

class KafkaProducer:
    def __init__(self):
        producer_config = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'acks': settings.KAFKA_PRODUCER_ACKS,
            'retries': settings.KAFKA_PRODUCER_RETRIES,
            'enable.idempotence': settings.KAFKA_PRODUCER_ENABLE_IDEMPOTENCE,
        }
        self.producer = Producer(producer_config)
        atexit.register(self.close)
        logger.info("Kafka producer initialized")

    def produce(
        self,
        topic: str,
        value: dict[str, Any] | str | bytes,
        key: str | bytes | None = None,
        headers: dict[str, str] | None = None,
    ):
        def delivery_report(err, msg):
            if err is not None:
                logger.error(f'[KAFKA_PRODUCER] Message delivery failed for topic {topic}: {err}')
            else:
                logger.info(f'[KAFKA_PRODUCER] Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}')

        if isinstance(value, dict):
            value = json.dumps(value).encode("utf-8")
        elif isinstance(value, str):
            value = value.encode("utf-8")

        if isinstance(key, str):
            key = key.encode("utf-8")

        kafka_headers = None
        if headers:
            kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]

        logger.info(f"[KAFKA_PRODUCER] Producing message to topic: {topic}, key: {key}")
        self.producer.produce(topic, value, key=key, headers=kafka_headers, callback=delivery_report)
        # Poll to trigger delivery callbacks and send buffered messages
        self.producer.poll(0)
        # For critical topics like usage logs, flush to ensure immediate delivery
        # Use a short timeout to avoid blocking too long
        if topic in ["llm-usage-logs"]:
            try:
                logger.info(f'[KAFKA_PRODUCER] Flushing messages for topic {topic}...')
                self.producer.flush(timeout=0.1)  # Non-blocking flush with 100ms timeout
                logger.info(f'[KAFKA_PRODUCER] Flush completed for topic {topic}')
            except Exception as e:
                logger.warning(f"[KAFKA_PRODUCER] Flush timeout for topic {topic}: {e}")

    def flush(self):
        self.producer.flush()

    def send_to_dlq(
        self, 
        message: Message, 
        entity_id: str,
        error_reason: str, 
        error_type: str,
        handler_name: str = "unknown"
    ):
        """
        Send failed message to Dead Letter Queue with error metadata.
        
        Args:
            message: Original Kafka message
            entity_id: ID of the entity that failed (conversation_id, etc.)
            error_reason: Detailed error message
            error_type: Type of error (parse_error, entity_not_found, indexing_failed, etc.)
            handler_name: Name of the handler that failed (elasticsearch-sync, etc.)
        """
        try:
            # Parse original message
            try:
                original_data = json.loads(message.value().decode('utf-8'))
            except:
                original_data = {"raw_message": message.value().decode('utf-8', errors='ignore')}
            
            # Create DLQ message with error metadata
            dlq_message = {
                "original_message": original_data,
                "error_metadata": {
                    "error_type": error_type,
                    "error_reason": error_reason,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "retry_count": 0,
                    "entity_id": entity_id,
                    "handler": handler_name,
                    "topic": message.topic(),
                    "partition": message.partition(),
                    "offset": message.offset()
                }
            }
            
            # Send to DLQ topic
            dlq_topic = self.config.KAFKA_DLQ_TOPIC
            
            self.producer.produce(
                dlq_topic,
                json.dumps(dlq_message).encode('utf-8'),
                key=entity_id.encode('utf-8')
            )
            self.producer.flush()
            
            logger.info(
                f"Sent message to DLQ: entity_id={entity_id}, "
                f"error_type={error_type}, topic={dlq_topic}"
            )
            
        except Exception as e:
            logger.error(f"Failed to send message to DLQ for entity {entity_id}: {e}")

    def close(self):
        logger.info("Flushing final Kafka messages...")
        self.producer.flush()
        logger.info("Kafka producer flushed.")


class BaseKafkaConsumer(ABC):
    """Base Kafka consumer"""
    
    def __init__(self, consumer: Consumer, handlers: List[MessageHandler]):
        self.consumer = consumer
        self.handlers = handlers
        
    @abstractmethod
    async def start(self):
        pass
        
    def initialise(self):
        """Setup signal handlers"""
        def signal_handler(sig, frame):
            logger.info("Caught signal, shutting down consumer...")
            if self.consumer:
                self.consumer.close()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


class SingleMessageConsumer(BaseKafkaConsumer):
    """
    Consumer that processes messages one at a time using poll().
    
    Benefits:
    - Low latency, immediate processing
    - Robust per-message error handling
    - Lower memory footprint
    - Simple offset management
    """
    
    async def start(self):
        """Process messages one at a time using poll()"""
        logger.info("Starting SingleMessageConsumer with poll() mode")
        
        try:
            poll_count = 0
            while True:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    poll_count += 1
                    # Log every 60 polls (approximately every minute) to show consumer is alive
                    if poll_count % 60 == 0:
                        logger.debug(f"Consumer polling... (poll #{poll_count}, no messages)")
                    continue
                    
                if msg.error():
                    logger.error(f"Message error: {msg.error()}")
                    continue
                
                # Reset poll count when we receive a message
                poll_count = 0
                logger.info(f"Received message from topic '{msg.topic()}' partition {msg.partition()} offset {msg.offset()}")
                
                # Process single message through all handlers
                try:
                    interim_output: InterimOutput = InterimOutput()
                    for handler in self.handlers:
                        logger.debug(f"Handler: {handler.__class__.__name__}")
                        try:
                            interim_output = await handler.handle(msg, interim_output)
                            logger.debug(f"Interim output: {interim_output}")
                        except Exception as e:
                            logger.exception(f"Error processing message with handler {handler.__class__.__name__}: {e}")
                            # Continue with other handlers even if one fails
                            continue
                except ValueError as e:
                    logger.error(f"Value error processing message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
        finally:
            if self.consumer:
                self.consumer.close()


class BulkMessageConsumer(BaseKafkaConsumer):
    """
    Consumer that processes messages in batches using consume().
    
    Benefits:
    - High throughput with bulk operations
    - Better resource utilization
    - Opportunity for deduplication and optimization
    - Reduced connection overhead
    """
    
    def __init__(self, consumer: Consumer, handlers: List[MessageHandler], 
                 max_poll_records: int, batch_timeout: float):
        super().__init__(consumer, handlers)
        self.max_poll_records = max_poll_records
        self.batch_timeout = batch_timeout
    
    async def start(self):
        """Process messages in batches using consume()"""
        logger.info(f"Starting BulkMessageConsumer with consume() mode "
                   f"(batch_size={self.max_poll_records}, timeout={self.batch_timeout}s)")
        
        try:
            while True:
                # Collect messages in batches
                messages = self.consumer.consume(
                    num_messages=self.max_poll_records,
                    timeout=self.batch_timeout
                )
                
                if not messages:
                    continue
                    
                # Filter out None messages and errors
                valid_messages = []
                for msg in messages:
                    if msg is None:
                        continue
                    if msg.error():
                        logger.error(f"Message error: {msg.error()}")
                        continue
                    valid_messages.append(msg)
                
                if not valid_messages:
                    continue
                    
                logger.info(f"Processing batch of {len(valid_messages)} messages")
                
                try:
                    interim_output: InterimOutput = InterimOutput()
                    for handler in self.handlers:
                        logger.debug(f"Handler: {handler.__class__.__name__}")
                        try:
                            # Check if handler supports bulk processing
                            if hasattr(handler, 'bulk_handle') and callable(getattr(handler, 'bulk_handle')):
                                logger.debug(f"Using bulk_handle for {handler.__class__.__name__}")
                                interim_output = await handler.bulk_handle(valid_messages, interim_output)
                            else:
                                logger.debug(f"Using individual handle for {handler.__class__.__name__}")
                                # Fallback to individual message processing
                                for msg in valid_messages:
                                    interim_output = await handler.handle(msg, interim_output)
                            
                            logger.debug(f"Interim output: {interim_output}")
                        except Exception as e:
                            logger.exception(f"Error processing batch with handler {handler.__class__.__name__}: {e}")
                            # Continue with other handlers even if one fails
                            continue
                            
                except ValueError as e:
                    logger.error(f"Value error processing batch: {e}")
                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                    
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
        finally:
            if self.consumer:
                self.consumer.close()


class ConsumerFactory:
    """Factory to create appropriate consumer based on configuration"""
    
    @staticmethod
    def get_instance(mode: str, consumer: Consumer, handlers: List[MessageHandler]) -> BaseKafkaConsumer:
        """
        Create appropriate consumer based on mode.
        
        Args:
            mode: "single" or "batch"
            consumer: Kafka Consumer instance
            handlers: List of message handlers
            
        Returns:
            Appropriate consumer instance
        """
        if mode == "batch":
            logger.info("Creating BulkMessageConsumer")
            return BulkMessageConsumer(
                consumer=consumer,
                handlers=handlers,
                max_poll_records=settings.KAFKA_CONSUMER_MAX_POLL_RECORDS,
                batch_timeout=settings.KAFKA_CONSUMER_BATCH_TIMEOUT_SECONDS
            )
        else:
            # Default to single message consumer
            if mode != "single":
                logger.warning(f"Unknown consumer mode '{mode}', defaulting to 'single'")
            logger.info("Creating SingleMessageConsumer")
            return SingleMessageConsumer(
                consumer=consumer,
                handlers=handlers
            )


# Global Instances
_kafka_producer: KafkaProducer | None = None

def get_kafka_producer() -> KafkaProducer:
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = KafkaProducer()
    return _kafka_producer

async def close_kafka() -> None:
    global _kafka_producer
    if _kafka_producer is not None:
        _kafka_producer.close()
        _kafka_producer = None


async def consume_messages():
    """Main entry point for Kafka message consumption"""
    
    # Kafka consumer configuration
    conf = {
        "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
        "group.id": settings.KAFKA_CONSUMER_GROUP_ID,
        "auto.offset.reset": settings.KAFKA_CONSUMER_AUTO_OFFSET_RESET,
    }

    consumer = Consumer(conf)
    import app.consumers.handlers  # noqa: F401
    handler_factory = MessageHandlerFactory()

    # Fetch the topics and handlers from the config
    topics = [
        topic.strip()
        for topic in settings.KAFKA_IN_TOPICS.split(",")
    ]
    logger.info(f"Topics: {topics}")

    # import handlers after decorator is defined so registration happens first
    from app.consumers import handlers as _handlers_module  # noqa: F401
    _handler_names = [
        handler_name.strip()
        for handler_name in settings.ENABLED_HANDLERS.split(",")
    ]
    logger.info(f"Handler names: {_handler_names}")
    handlers = [handler_factory.get_handler(handler_name) for handler_name in _handler_names]
    logger.info(f"Handlers: {handlers}")
    
    # Subscribe to topics
    consumer.subscribe(topics)
    logger.info(f"Subscribed to topics: {topics}")
    
    # Create appropriate consumer based on configuration
    kafka_consumer = ConsumerFactory.get_instance(
        mode=settings.KAFKA_CONSUMER_MODE,
        consumer=consumer,
        handlers=handlers
    )
    
    # Setup signal handlers for graceful shutdown
    kafka_consumer.initialise()
    
    # Start consumption loop
    await kafka_consumer.start()

if __name__ == "__main__":
    import sys
    from app.core.adapter.redis import init_redis, close_redis
    from app.core.adapter.postgres import init_postgres, close_postgres
    
    # Check if test connection is requested
    if len(sys.argv) > 1 and sys.argv[1] == "--test-connection":
        # Test connection only
        conf = {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": settings.KAFKA_CONSUMER_GROUP_ID,
            "auto.offset.reset": settings.KAFKA_CONSUMER_AUTO_OFFSET_RESET,
        }
        
        consumer = Consumer(conf)
        
        try:
            logger.info(f"Testing connection to Kafka at {settings.KAFKA_BOOTSTRAP_SERVERS}...")
            metadata = consumer.list_topics(timeout=5.0)
            logger.info(f"✅ Successfully connected to Kafka!")
            logger.info(f"Available topics: {list(metadata.topics.keys())}")
            consumer.close()
            sys.exit(0)
        except Exception as e:
            logger.error(f"❌ Failed to connect to Kafka: {e}")
            logger.error("Possible solutions:")
            logger.error("  1. Make sure Kafka is running: docker-compose up kafka")
            logger.error("  2. For local testing, set KAFKA_BOOTSTRAP_SERVERS=localhost:9092")
            logger.error("  3. For Docker network, set KAFKA_BOOTSTRAP_SERVERS=kafka:9092")
            consumer.close()
            sys.exit(1)
    else:
        # Normal operation
        async def main():
            logger.info("Starting Kafka consumer worker")
            await init_redis()
            await init_postgres()
            import app.consumers.handlers  # noqa: F401

            try:
                await consume_messages()
            finally:
                await close_redis()
                await close_postgres()
                logger.info("Kafka consumer worker stopped")

        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            pass
