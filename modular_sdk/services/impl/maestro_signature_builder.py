import base64
import hashlib
import hmac
import json
import os
import time
from modular_sdk.commons.constants import PLAIN_CONTENT_TYPE


class MaestroSignatureBuilder:
    __slots__ = '_access_key', '_secret_key', '_user'

    def __init__(self, access_key: str, secret_key: str, user: str):
        self._access_key = access_key
        self._secret_key = secret_key
        self._user = user

    def decrypt(self, data: bytes | str) -> bytes:
        """
        Decode received message from Base64 format, cut initialization
        vector ("iv") from beginning of the message, decrypt message
        """
        from cryptography.hazmat.primitives.ciphers import (
            Cipher, algorithms, modes,
        )
        decoded_data = base64.b64decode(data)
        iv = decoded_data[:12]
        encrypted_data = decoded_data[12:]
        cipher = Cipher(
            algorithms.AES(key=self._secret_key.encode('utf-8')),
            modes.GCM(initialization_vector=iv)
        ).decryptor()
        origin_data_with_iv = cipher.update(encrypted_data)
        # Due to Initialization vector in encrypting method
        # there is need to split useful and useless parts of the
        # server response.
        response = origin_data_with_iv[:-16]
        return response

    def encrypt(self, data: str | dict | list) -> bytes:
        """
        Encrypt data, add initialization vector ("iv") at beginning of encrypted
        message and encode entire data in Base64 format
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        iv = os.urandom(12)
        plain_text = data if isinstance(data, str) else json.dumps(
            data,
            separators=(',', ':')
        )
        data_in_bytes = plain_text.encode('utf-8')
        try:
            cipher = AESGCM(key=self._secret_key.encode('utf-8'))
        except ValueError as e:
            raise ValueError(str(e).replace('AESGCM key', 'Secret Key'))
        encrypted_data = cipher.encrypt(
            nonce=iv, data=data_in_bytes, associated_data=None)
        return base64.b64encode(iv + encrypted_data)

    def get_signed_headers(self, async_request: bool = False,
                           compressed: bool = False) -> dict:
        """
        Create and sign necessary headers for interaction with Maestro API
        """
        date = int(time.time() * 1000)
        signature = hmac.new(
            key=f'{self._secret_key}{date}'.encode('utf-8'),
            msg=f'M3-POST:{self._access_key}:{date}:{self._user}'.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        n = 2
        resolved_signature = ''
        for each in [signature[i:i + n] for i in range(0, len(signature), n)]:
            resolved_signature += '1' + each
        return {
            "maestro-authentication": resolved_signature,
            "maestro-request-identifier": "api-server",
            "maestro-user-identifier": self._user,
            "maestro-date": str(date),
            "maestro-accesskey": str(self._access_key),
            "maestro-sdk-version": "3.2.80",
            "maestro-sdk-async": 'true' if async_request else 'false',
            "compressed": True if compressed else False,
        }

    def get_http_signed_headers(self, async_request: bool = False, 
                                compressed: bool = False) -> dict:
        base = self.get_signed_headers(async_request=async_request, 
                                       compressed=compressed)
        base['compressed'] = 'true' if base['compressed'] else 'false'
        base['Content-Type'] = PLAIN_CONTENT_TYPE
        return base

