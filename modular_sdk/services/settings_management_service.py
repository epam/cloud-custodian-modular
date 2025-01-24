import json
import os
import re
from http import HTTPStatus

from modular_sdk.commons import ModularException
from modular_sdk.commons.log_helper import get_logger
from modular_sdk.models.setting import Setting

_LOG = get_logger(__name__)


class SettingsManagementService:
    def __init__(self, group_name: str):
        self.group_name = group_name.upper()

    def create_setting_item(self, setting_key, setting_value):
        if isinstance(setting_key, str):
            setting_key = setting_key.upper()
        self._validate_setting_key(setting_key=setting_key)
        setting_value = self._validate_setting_value(
            setting_key=setting_key,
            setting_value=setting_value
        )
        if self.describe_setting_item(setting_key=setting_key):
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'{setting_key} setting already exists. Please use '
                        f'\'update\' command instead.'
            )
        setting_item = Setting(name=setting_key,
                               value=setting_value)
        setting_item.save()

    def update_setting_item(self, setting_key, setting_value):
        if isinstance(setting_key, str):
            setting_key = setting_key.upper()
        self._validate_setting_key(setting_key=setting_key)
        setting_value = self._validate_setting_value(
            setting_key=setting_key,
            setting_value=setting_value
        )
        if not self.describe_setting_item(setting_key=setting_key):
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'{setting_key} setting does not exist. Please use '
                        f'\'add\' command first.'
            )

        setting_item = Setting(name=setting_key,
                               value=setting_value)
        setting_item.save()

    def describe_setting_item(self, setting_key):
        if isinstance(setting_key, str):
            setting_key = setting_key.upper()
        self._validate_setting_key(setting_key=setting_key)
        return Setting.get_nullable(setting_key)

    def list_setting_items(self):
        return list(Setting.scan(
            filter_condition=(Setting.name.startswith(self.group_name))
        ))

    def delete_setting_item(self, setting_key):
        if isinstance(setting_key, str):
            setting_key = setting_key.upper()
        self._validate_setting_key(setting_key)
        if not Setting.get_nullable(setting_key):
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'{setting_key} setting not found.'
            )
        Setting(name=setting_key).delete()

    def _validate_setting_key(self, setting_key: str):
        regex = r"^{0}(?![\da-zA-Z])".format(self.group_name)
        if not re.match(regex, setting_key):
            _LOG.error('Invalid setting name')
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'{setting_key} setting does not belongs to '
                        f'{self.group_name} group'
            )

    def _validate_setting_value(self, setting_key: str, setting_value: str):
        # bool validation
        boolean_markers = ['_ENABLED', '_DISABLED', '_ACTIVE',
                           '_RUNNING', '_AVAILABLE']  # + '_IS_', '_ARE_'
        for mark in boolean_markers:
            if setting_key.endswith(mark) or '_IS_' in setting_key:
                return self.__process_boolean_value(setting_value)
            if '_ARE_' in setting_key:
                return self.__process_boolean_value(setting_value)

        # list validation
        if setting_key.endswith('_LIST'):
            return self.__process_list_value(setting_value)

        # map validation
        map_markers = ['_JSON', '_MAP', '_MAPPING']
        for mark in map_markers:
            if setting_key.endswith(mark):
                return self.__process_map_value(setting_value)

        # integer validation
        int_markers = ['_COUNT', '_THRESHOLD', '_LONG', '_INT']
        for mark in int_markers:
            if setting_key.endswith(mark):
                return self.__process_integer_value(setting_value)
            if setting_key.endswith('_EXPIRATION'):
                return self.__process_milliseconds_value(setting_value)

        # email validation
        if setting_key.endswith('_MAIL'):
            return self.__process_email_value(setting_value)

        # url validation
        if setting_key.endswith('_URL'):
            return self.__process_url_value(setting_value)

        # for all other cases
        return self.__process_regular_value(setting_value)

    @staticmethod
    def __process_boolean_value(setting_value):
        if setting_value.lower() not in ('true', 'false'):
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'Setting name matches to the one from the following '
                        f'patterns: *_IS_* / *_ARE_* / *_ENABLED / *_DISABLED / '
                        f'*_ACTIVE / *_RUNNING / *_AVAILABLE{os.linesep}'
                        f'Invalid value provided for bool type setting. '
                        f'Expected "True" or "False", case-insensitive. '
            )
        setting_value = True if setting_value.lower() == 'true' else False
        return setting_value

    @staticmethod
    def __process_email_value(setting_value):
        import re
        if not re.match(
                r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)',
                setting_value
        ):
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'Setting name matches to the pattern: *_MAIL{os.linesep}'
                        f'Invalid email provided, check spelling.'
            )
        return setting_value

    @staticmethod
    def __process_milliseconds_value(setting_value):
        invalid_length = False
        if len(setting_value) != 13:
            invalid_length = True
        try:
            import datetime
            if invalid_length:
                raise ValueError()
            if setting_value.startswith('0'):
                raise ValueError()
            timestamp_in_seconds = int(setting_value) / 1000
            if timestamp_in_seconds < 0:
                raise ValueError()
            datetime.datetime.fromtimestamp(timestamp_in_seconds)
            return int(setting_value)
        except (TypeError, ValueError, OSError):
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'Setting name matches to the pattern: *_EXPIRATION{os.linesep}'
                        f'Invalid value provided for expiration setting. '
                        f'Expected EPOCH milliseconds format, 13 digits, '
                        f'positive integer number'
            )

    @staticmethod
    def __process_url_value(setting_value):
        try:
            from urllib.parse import urlparse
            result = urlparse(setting_value)
            if not all([result.scheme, result.netloc]):
                raise AssertionError()
            return setting_value
        except AssertionError:
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'Setting name matches to the pattern: *_URL{os.linesep}'
                        f'Invalid value provided for URL link, check spelling. '
                        f'Format: <$protocol>://<$net_location>'
            )

    @staticmethod
    def __process_integer_value(setting_value):
        try:
            setting_value = int(setting_value)
            return setting_value
        except (TypeError, ValueError):
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'Setting name matches to the one from the following '
                        f'patterns: *_COUNT, *_THRESHOLD, *_LONG, *_INT{os.linesep}'
                        f'Invalid value provided. Expected integer value.'
            )

    @staticmethod
    def __process_map_value(setting_value):
        if isinstance(setting_value, dict):
            return setting_value
        try:
            result = json.loads(setting_value)
        except json.JSONDecodeError:
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'Setting name matches to the one from the following '
                        f'patterns: *_JSON / *_MAP / *_MAPPING{os.linesep}'
                        f'Value format is \'Escaped string\'.{os.linesep}'
                        f'Invalid JSON object provided.'
            )
        return result

    @staticmethod
    def __process_list_value(setting_value):
        if isinstance(setting_value, list):
            return setting_value
        result_value = []
        setting_value_list = setting_value.split(',')
        for item in setting_value_list:
            value = item.strip()
            try:
                result_value.append(int(value))
                continue
            except ValueError:
                pass
            try:
                result_value.append(float(value))
                continue
            except ValueError:
                pass
            result_value.append(value)
        return result_value

    @staticmethod
    def __process_regular_value(setting_value):
        try:
            return int(setting_value)
        except ValueError:
            pass
        try:
            return float(setting_value)
        except ValueError:
            pass
        return setting_value
