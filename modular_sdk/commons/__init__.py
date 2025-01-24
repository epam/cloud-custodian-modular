import base64
import dataclasses
import gzip
import json
import warnings
from functools import partial
from uuid import uuid4
from typing import Generator, TypeVar

from modular_sdk.commons.exception import ModularException
from modular_sdk.commons.log_helper import get_logger

_LOG = get_logger(__name__)


def deprecated(message):
    def deprecated_decorator(func):
        def deprecated_func(*args, **kwargs):
            warnings.warn(
                "{} is a deprecated function. {}".format(func.__name__,
                                                         message),
                category=DeprecationWarning,
                stacklevel=2)
            warnings.simplefilter('default', DeprecationWarning)
            return func(*args, **kwargs)

        return deprecated_func

    return deprecated_decorator


def get_missing_parameters(event, required_params_list):
    missing_params_list = []
    for param in required_params_list:
        if event.get(param) is None:
            missing_params_list.append(param)
    return missing_params_list


def validate_params(event, required_params_list):
    """
    Checks if all required parameters present in lambda payload.
    :param event: the lambda payload
    :param required_params_list: list of the lambda required parameters
    :return: bad request response if some parameter[s] is/are missing,
        otherwise - none
    """
    missing_params_list = get_missing_parameters(event, required_params_list)

    if missing_params_list:
        raise ValueError('The following parameters '
                         'are missing: {0}'.format(missing_params_list))


def generate_id():
    return str(uuid4())


def generate_id_hex():
    return str(uuid4().hex)


def build_secure_message(
        request_id: str,
        command_name: str,
        parameters_to_secure: dict,
        secure_parameters: list[str] | None = None,
        is_flat_request: bool = False,
) -> list[dict] | str:
    if not secure_parameters:
        secure_parameters = []
    secured_parameters = {
        k: (v if k not in secure_parameters else '*****')
        for k, v in parameters_to_secure.items()
    }
    return build_message(
        request_id=request_id,
        command_name=command_name,
        parameters=secured_parameters,
        is_flat_request=is_flat_request,
    )


def build_message(
        request_id: str,
        command_name: str,
        parameters: list[dict] | dict,
        is_flat_request: bool = False,
        compressed: bool = False,
) -> list[dict] | str:
    if isinstance(parameters, list):
        result = []
        for payload in parameters:
            result.extend(
                build_payload(request_id, command_name, payload, is_flat_request)
            )
    else:
        result = \
            build_payload(request_id, command_name, parameters, is_flat_request)
    if compressed:
        return base64 \
            .b64encode(gzip.compress(json.dumps(result, separators=(',', ':')).encode('UTF-8'))).decode()
    return result


def build_payload(
        request_id: str,
        command_name: str,
        parameters: dict,
        is_flat_request: bool,
) -> list[dict]:
    if is_flat_request:
        parameters.update({'type': command_name})
        result = [{'id': request_id, 'type': None, 'params': parameters}]
    else:
        result = [{'id': request_id, 'type': command_name,'params': parameters}]
    return result


def default_instance(value, _type: type, *args, **kwargs):
    return value if isinstance(value, _type) else _type(*args, **kwargs)


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class DataclassBase:
    """
    Provides some useful methods for dataclass instances.
    Ignore warnings below
    """

    @staticmethod
    def _factory(x: dict, exclude: set = None) -> dict:
        dct = {k: v for k, v in x if v is not None}
        if exclude:
            [dct.pop(key, None) for key in exclude]
        return dct

    def dict(self, exclude: set = None) -> dict:
        return dataclasses.asdict(
            self, dict_factory=partial(self._factory, exclude=exclude)
        )

    @classmethod
    def from_dict(cls, dct: dict):
        """
        Ignoring extra kwargs
        :param dct:
        :return:
        """
        return cls(**{
            k.name: dct.get(k.name) for k in dataclasses.fields(cls)
        })


T = TypeVar('T')


def iter_subclasses(cls: type[T]) -> Generator[type[T], None, None]:
    """
    Recursively iterates over subclasses and their subclasses. Does not handle
    duplicates in case of multiple inheritance.
    """
    for item in cls.__subclasses__():
        yield item
        yield from iter_subclasses(item)


def iter_subclasses_unique(cls: type[T]) -> Generator[type[T], None, None]:
    yielded = set()
    for item in iter_subclasses(cls):
        _id = id(item)
        if _id in yielded:
            continue
        yield item
        yielded.add(_id)
