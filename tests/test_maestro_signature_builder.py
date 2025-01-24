import json
import random
import secrets
from unittest.mock import patch

import pytest

from modular_sdk.services.impl.maestro_signature_builder import \
    MaestroSignatureBuilder
_cryptography = True
try:
    import cryptography
except ImportError:
    _cryptography = False


@pytest.fixture
def secret_key() -> str:
    return secrets.token_hex(random.choice((8, 12, 16)))


@pytest.mark.skipif(not _cryptography, reason='cryptography is not installed')
def test_encrypt_decrypt(secret_key):
    signer = MaestroSignatureBuilder(
        access_key='access_key',
        secret_key=secret_key,
        user='user'
    )
    data = 'my-secret-data'
    assert signer.decrypt(signer.encrypt(data)) == data.encode()

    data = [1, 2, 3, 'my-data']
    assert json.loads(signer.decrypt(signer.encrypt(data))) == data

    data = {'key': 'value', 'list': [1, 2, {'key1': 'value1'}]}
    assert json.loads(signer.decrypt(signer.encrypt(data))) == data


@pytest.mark.skipif(not _cryptography, reason='cryptography is not installed')
def test_encrypt():
    signer = MaestroSignatureBuilder(
        access_key='access_key',
        secret_key='1234567890123456',
        user='user'
    )
    with patch('os.urandom', lambda x: b'1' * 12):
        val = signer.encrypt('secret-data')
    assert val == b'MTExMTExMTExMTEx4pEMpmk6f+Ih4nJj3fK21M1TpP3VE/r/pggy'


@pytest.mark.skipif(not _cryptography, reason='cryptography is not installed')
def test_decrypt():
    signer = MaestroSignatureBuilder(
        access_key='access_key',
        secret_key='1234567890123456',
        user='user'
    )
    assert signer.decrypt(
        b'kVUII6Yho1wGMkVQuKP8vFjt5iTwAoEWrrwqgSVx251IeXBcbP3AHQ==') == b'secret-data2'


def test_get_headers():
    signer = MaestroSignatureBuilder(
        access_key='access_key',
        secret_key='1234567890123456',
        user='user'
    )
    with patch('time.time', lambda: 1728655109.171027):
        headers = signer.get_signed_headers(
            async_request=True,
            compressed=True
        )
        assert headers == {
            'maestro-authentication': '19a1e711211517d16a1d015910a1141191a111111f12b16714714a1b41941111001c319b13e10114b1d412417b1f21e9',
            'maestro-request-identifier': 'api-server',
            'maestro-user-identifier': 'user', 'maestro-date': '1728655109171',
            'maestro-accesskey': 'access_key', 'maestro-sdk-version': '3.2.80',
            'maestro-sdk-async': 'true', 'compressed': True
        }


def test_get_http_headers():
    signer = MaestroSignatureBuilder(
        access_key='access_key',
        secret_key='1234567890123456',
        user='user'
    )
    with patch('time.time', lambda: 1728655109.171027):
        headers = signer.get_http_signed_headers(
            async_request=True,
            compressed=True
        )
        assert headers == {
            'maestro-authentication': '19a1e711211517d16a1d015910a1141191a111111f12b16714714a1b41941111001c319b13e10114b1d412417b1f21e9',
            'maestro-request-identifier': 'api-server',
            'maestro-user-identifier': 'user', 'maestro-date': '1728655109171',
            'maestro-accesskey': 'access_key', 'maestro-sdk-version': '3.2.80',
            'maestro-sdk-async': 'true', 'compressed': 'true', 
            'Content-Type': 'text/plain'
        }
