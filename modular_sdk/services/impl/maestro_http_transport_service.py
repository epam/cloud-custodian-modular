import binascii
import json
import urllib.request
import threading
import urllib.parse
import urllib.error
from typing import Any
from modular_sdk.commons import ModularException, generate_id, build_message
from modular_sdk.commons.constants import SUCCESS_STATUS
from modular_sdk.commons.log_helper import get_logger
from modular_sdk.services.impl.maestro_signature_builder import (
    MaestroSignatureBuilder,
)
from modular_sdk.services.rabbit_transport_service import AbstractTransport

HTTP_DEFAULT_RESPONSE_TIMEOUT = 30
_LOG = get_logger(__name__)


class MaestroHTTPConfig:
    def __init__(
            self,
            sdk_access_key: str,
            sdk_secret_key: str,
            maestro_user: str,
    ):
        self.sdk_access_key = sdk_access_key
        self.sdk_secret_key = sdk_secret_key
        self.maestro_user = maestro_user


class MaestroHTTPTransport(AbstractTransport):
    def __init__(
            self,
            config: MaestroHTTPConfig,
            api_link: str,
            timeout: int | None = HTTP_DEFAULT_RESPONSE_TIMEOUT,
    ):
        self.access_key = config.sdk_access_key
        self.secret_key = config.sdk_secret_key
        self.user = config.maestro_user
        self.api_link = api_link
        self.timeout = timeout or HTTP_DEFAULT_RESPONSE_TIMEOUT

    def pre_process_request(self, command_name: str, parameters: list[dict] | dict,
                            is_flat_request: bool = False,
                            async_request: bool = False,
                            compressed: bool = False, config=None, **kwargs
                            ) -> tuple[bytes, dict]:
        request_id = generate_id()
        _LOG.debug('Going to pre-process HTTP request')
        message = build_message(
            command_name=command_name,
            parameters=parameters,
            request_id=request_id,
            is_flat_request=is_flat_request,
            compressed=compressed,
        )
        _LOG.info(f'Going to send rabbit '
                  f'request: {command_name=}, {request_id=}, '
                  f'{is_flat_request=}')

        signer = MaestroSignatureBuilder(
            access_key=config.sdk_access_key if config and config.sdk_access_key else self.access_key,
            secret_key=config.sdk_secret_key if config and config.sdk_secret_key else self.secret_key,
            user=config.maestro_user if config and config.maestro_user else self.user,
        )
        encrypted_body = signer.encrypt(data=message)

        _LOG.debug('Message encrypted')
        # sign headers
        headers = signer.get_http_signed_headers(
            async_request=async_request, compressed=compressed,
        )
        _LOG.debug('Signed headers prepared')
        return encrypted_body, headers

    def post_process_request(self, response: bytes) -> tuple[int, str, Any]:
        signer = MaestroSignatureBuilder(
            access_key=self.access_key,
            secret_key=self.secret_key,
            user=self.user,
        )
        try:
            response_item = signer.decrypt(data=response)
            _LOG.debug('Message from M3-server successfully decrypted')
        except binascii.Error:
            response_item = response.decode('utf-8')
        try:
            _LOG.debug(f'Raw decrypted message from server: {response_item}')
            response_json = json.loads(response_item).get('results')[0]
        except json.decoder.JSONDecodeError:
            _LOG.error('Response cannot be decoded - invalid JSON string')
            raise ModularException(code=502, content="Response can't be decoded")
        status = response_json.get('status')
        code = response_json.get('statusCode')
        if status == SUCCESS_STATUS:
            data = response_json.get('data')
        else:
            data = response_json.get('readableError') or response_json.get('error')
        return code, status, data

    def send_sync(self, command_name: str, parameters: list[dict] | dict,
                  is_flat_request: bool = False, async_request: bool = False,
                  compressed: bool = False, config=None, **kwargs
                  ) -> tuple[int, str, Any]:
        _LOG.debug('Making sync http request ')
        message, headers = self.pre_process_request(
            command_name=command_name,
            parameters=parameters,
            is_flat_request=is_flat_request,
            async_request=async_request,
            compressed=compressed,
            config=config
        )
        req = urllib.request.Request(
            url=self.api_link, headers=headers, data=message, method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                _LOG.debug(
                    f'Response status code: {response.getcode()}, reason: {response.reason}')
                return self.post_process_request(response.read())
        except urllib.error.HTTPError as e:
            raise ModularException(code=e.getcode(), content=e.read().decode())
        except urllib.error.URLError as e:
            _LOG.exception('Cannot make a request')
            raise ModularException(code=502,
                                   content='Could not make the request')

    def send_async(self, *args, **kwargs) -> None:
        message, headers = self.pre_process_request(*args, **kwargs)
        req = urllib.request.Request(
            url=self.api_link, headers=headers, data=message, method='POST',
        )

        def _send(r, t):
            with urllib.request.urlopen(r, timeout=t) as resp:
                _LOG.info('Async request sent. No response will be processed')

        threading.Thread(target=_send, args=(req, self.timeout)).start()
