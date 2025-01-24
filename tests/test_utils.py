import base64
import gzip
import json

import pytest
from modular_sdk.commons import (
    build_message,
    build_payload,
    build_secure_message,
    iter_subclasses,
    iter_subclasses_unique,
)


@pytest.fixture
def dict_sample() -> dict:
    return {
        'str': 'str',
        'map': {'str': 'str', 'map': {'str': 'str', 'list': ['one', 'two']}},
        'list': [{'str': 'str', 'list': ['one', 'two']}],
    }


def test_build_payload():
    assert build_payload('id', 'name', {'key': 'value'}, False) == [
        {'id': 'id', 'type': 'name', 'params': {'key': 'value'}}
    ]
    assert build_payload('id', 'name', {'key': 'value'}, True) == [
        {'id': 'id', 'type': None, 'params': {'key': 'value', 'type': 'name'}}
    ]


def test_build_message():
    assert build_message(
        'id', 'name', [{'key1': 'value1'}, {'key2': 'value2'}]
    ) == [
        {'id': 'id', 'type': 'name', 'params': {'key1': 'value1'}},
        {'id': 'id', 'type': 'name', 'params': {'key2': 'value2'}},
    ]
    assert build_message('id', 'name', {'key1': 'value1'}) == [
        {'id': 'id', 'type': 'name', 'params': {'key1': 'value1'}}
    ]

    assert build_message('id', 'name', {'key1': 'value1'}, True) == [
        {
            'id': 'id',
            'type': None,
            'params': {'key1': 'value1', 'type': 'name'},
        }
    ]

    res = build_message('id', 'name', {'key1': 'value1'}, True, True)
    assert json.loads(gzip.decompress(base64.b64decode(res))) == [
        {
            'id': 'id',
            'type': None,
            'params': {'key1': 'value1', 'type': 'name'},
        }
    ]


def test_build_secure_message():
    # weird thing
    assert build_secure_message(
        'id', 'name', {'key': 'value', 'key1': 'value1'}, ['key'], True
    ) == [
        {
            'id': 'id',
            'type': None,
            'params': {'key': '*****', 'key1': 'value1', 'type': 'name'},
        }
    ]


def test_iter_subclasses():
    class A:
        pass

    assert list(iter_subclasses(A)) == []

    class B(A):
        pass

    assert list(iter_subclasses(A)) == [B]

    class C(B):
        pass

    class D(B):
        pass

    assert list(iter_subclasses(A)) == [B, C, D]

    class E(A):
        pass

    assert list(iter_subclasses(A)) == [B, C, D, E]


def test_iter_subclasses_diamond():
    class A:
        pass

    class B(A):
        pass

    class C(A):
        pass

    class D(B, C):
        pass

    assert list(iter_subclasses(A)) == [B, D, C, D]
    assert list(iter_subclasses_unique(A)) == [B, D, C]
