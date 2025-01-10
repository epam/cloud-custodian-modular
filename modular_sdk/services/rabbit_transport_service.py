from abc import abstractmethod
from typing import TYPE_CHECKING, Any
from pika import exceptions
from modular_sdk.commons import ModularException, generate_id_hex
from modular_sdk.commons.constants import PLAIN_CONTENT_TYPE
from modular_sdk.commons.log_helper import get_logger

if TYPE_CHECKING:
    from modular_sdk.connections.rabbit_connection import RabbitMqConnection

_LOG = get_logger(__name__)


class AbstractTransport:
    def send_sync(self, *args, **kwargs) -> tuple[int, str, Any]:
        """
        Can raise ModularException
        """

    def send_async(self, *args, **kwargs) -> None:
        pass


class RabbitConfig:
    def __init__(self, request_queue: str, response_queue: str,
                 rabbit_exchange: str):
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.rabbit_exchange = rabbit_exchange


class RabbitMQTransport(AbstractTransport):
    def __init__(self, rabbit_connection: 'RabbitMqConnection',
                 config: RabbitConfig):
        self.rabbit = rabbit_connection
        self.request_queue = config.request_queue
        self.response_queue = config.response_queue
        self.exchange = config.rabbit_exchange

    @abstractmethod
    def pre_process_request(self, *args, **kwargs) -> tuple[str | bytes, dict]:
        """
        Must return tuple that contains message and headers
        """

    @abstractmethod
    def post_process_request(self, *args, **kwargs) -> tuple[int, str, str]:
        """
        Must return a tuple that contains code status and response
        """

    def __resolve_rabbit_options(self, exchange, request_queue,
                                 response_queue) -> tuple[str, str, str]:
        exchange = exchange or self.exchange
        if exchange:
            routing_key = ''
        else:
            routing_key = request_queue or self.request_queue
            exchange = ''

        response_queue = response_queue if response_queue else self.response_queue
        return routing_key, exchange, response_queue

    def send_sync(self, *args, **kwargs) -> tuple[int, str, Any]:
        message, headers = self.pre_process_request(*args, **kwargs)
        rabbit_config = kwargs.get('config')
        request_queue, exchange, response_queue = \
            self.__resolve_rabbit_options(
                exchange=rabbit_config.rabbit_exchange if rabbit_config else None,
                request_queue=rabbit_config.request_queue if rabbit_config else None,
                response_queue=rabbit_config.response_queue if rabbit_config else None
            )

        correlation_id = generate_id_hex()
        self.rabbit.publish_sync(routing_key=request_queue,
                                 exchange=exchange,
                                 callback_queue=response_queue,
                                 correlation_id=correlation_id,
                                 message=message,
                                 headers=headers,
                                 content_type=PLAIN_CONTENT_TYPE)
        try:
            response_item = self.rabbit.consume_sync(
                queue=response_queue, correlation_id=correlation_id,
            )
        except exceptions.ConnectionWrongStateError as e:
            raise ModularException(code=502, content=str(e))

        if not response_item:
            raise ModularException(
                code=502,
                content=f'Response was not received. '
                        f'Timeout: {self.rabbit.timeout} seconds.'
            )
        return self.post_process_request(response=response_item)

    def send_async(self, *args, **kwargs) -> None:
        message, headers = self.pre_process_request(*args, **kwargs)
        rabbit_config = kwargs.get('config')
        request_queue, exchange, response_queue = \
            self.__resolve_rabbit_options(
                exchange=rabbit_config.exchange if rabbit_config else None,
                request_queue=rabbit_config.request_queue if rabbit_config else None,
                response_queue=rabbit_config.response_queue if rabbit_config else None
            )

        return self.rabbit.publish(
            routing_key=request_queue,
            exchange=exchange,
            message=message,
            headers=headers,
            content_type=PLAIN_CONTENT_TYPE)
