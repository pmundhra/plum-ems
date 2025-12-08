import logging
from abc import ABC, abstractmethod
from typing import Callable, Dict, Type, Any, List

from confluent_kafka import Message
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


message_handler_registry: Dict[str, Type["MessageHandler"]] = {}


class InterimOutput(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class MessageHandler(ABC):
    @abstractmethod
    async def handle(self, message: Message, interim_output: InterimOutput) -> InterimOutput:
        """Handles the received message from Kafka."""
        pass
    
    async def bulk_handle(self, messages: List[Message], interim_output: InterimOutput) -> InterimOutput:
        """
        Handles multiple messages in bulk. Default implementation calls handle() for each message.
        Override this method in handlers that can benefit from bulk processing.
        
        Args:
            messages: List of Kafka messages to process
            interim_output: Shared output object for passing data between handlers
            
        Returns:
            Updated InterimOutput object
        """
        logger.debug(f"Processing {len(messages)} messages individually (default bulk_handle implementation)")
        for message in messages:
            try:
                interim_output = await self.handle(message, interim_output)
            except Exception as e:
                logger.error(f"Error processing message in bulk_handle: {e}")
                # Continue processing other messages even if one fails
                continue
        return interim_output


def handler(
    name: str,
) -> Callable[[Type[MessageHandler]], Type[MessageHandler]]:
    """
    Decorator to register a message handler for a specific topic.
    """

    def decorator(cls: Type[MessageHandler]) -> Type[MessageHandler]:
        if name in message_handler_registry:
            logger.warning(f"Handler for topic '{name}' is being overridden.")
        message_handler_registry[name] = cls
        return cls

    return decorator


class MessageHandlerFactory:
    def __init__(self):
        self._handlers: Dict[str, MessageHandler] = {}
        self._load_handlers()

    def _load_handlers(self):
        for name, handler_class in message_handler_registry.items():
            try:
                self._handlers[name] = handler_class()
                logger.info(
                    f"Loaded handler '{handler_class.__name__}'('{name}')."
                )
            except Exception as e:
                logger.error(
                    "An unexpected error occurred while loading handler"
                    f" '{name}': {e}"
                )

    def get_handler(self, name: str) -> MessageHandler:
        handler = self._handlers.get(name)
        if handler:
            return handler

        default_handler_instance = self._handlers.get("default")
        if default_handler_instance:
            return default_handler_instance

        logger.warning(
            f"No handler found for name '{name}' and no default handler is configured."
        )
        raise ValueError(f"No handler for topic {name}")
