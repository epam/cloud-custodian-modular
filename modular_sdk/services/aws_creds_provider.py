from typing import Optional

import boto3
from botocore.client import BaseClient
from datetime import datetime, timedelta

from modular_sdk.modular import Modular
from modular_sdk.commons.time_helper import utc_datetime
from functools import cached_property

from modular_sdk.commons.log_helper import get_logger

_LOG = get_logger(__name__)


class AWSCredentialsProvider:  # client provider
    def __init__(self, service_name: str, aws_region: str,
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 aws_session_token: Optional[str] = None):
        if bool(aws_access_key_id) ^ bool(aws_secret_access_key):
            error_message = 'aws_access_key_id and aws_secret_access_key ' \
                            'must be both specified.'
            raise KeyError(error_message)  # RuntimeError

        self._service_name = service_name
        self._region_name = aws_region
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._aws_session_token = aws_session_token

    @cached_property
    def client(self) -> BaseClient:
        _LOG.info(f'Initializing {self._service_name} boto3 client')
        return boto3.client(
            service_name=self._service_name,
            region_name=self._region_name,
            aws_access_key_id=self._aws_access_key_id,
            aws_secret_access_key=self._aws_secret_access_key,
            aws_session_token=self._aws_session_token,
        )


class ModularAssumeRoleClient:
    """
    Descriptor class for boto3 client attributes when we need them to
    be refreshed when modular_sdk assume role creds expire. Example:

    class SSMClient:
        client = ModularAssumeRoleClient('ssm')

        def get_parameter(self, name):
            return self.client.get_parameter(Name=name, WithDecryption=True)

    Such a client will be automatically refreshed.
    """
    session: boto3.Session = None  # class var
    exp: datetime = None  # class var, session's creds expiration

    def __init__(self, service_name: str,
                 region_name: Optional[str] = None):
        # TODO add role_arn to input params
        self._service_name = service_name
        self._region_name = region_name
        self._client: Optional[BaseClient] = None

    @classmethod
    def get_session(cls) -> boto3.Session:
        if not cls.session:
            _LOG.info('Initializing boto3 session inside '
                      'ModularAssumeRoleClient descriptor')
            cls.session = boto3.Session()
        return cls.session

    @classmethod
    def _expired(cls) -> bool:
        in_a_while = utc_datetime() + timedelta(minutes=5)
        return not isinstance(cls.exp, datetime) or in_a_while > cls.exp

    @classmethod
    def _update_session(cls, aws_access_key_id: str,
                        aws_secret_access_key: str,
                        aws_session_token: str,
                        expiration: datetime):
        cls.get_session()._session.set_credentials(
            access_key=aws_access_key_id,
            secret_key=aws_secret_access_key,
            token=aws_session_token
        )
        cls.exp = expiration

    def __get__(self, instance, owner) -> BaseClient:
        """
        We cannot use sts.assure_modular_credentials_valid() and
        BaseRoleAccessModel's logic here as well (I mean creds from envs)
        because here we cannot catch the moment when creds were refreshed by
        models, for instance. Think about it
        """
        _modular = Modular()
        sts, env = _modular.sts_service(), _modular.environment_service()
        roles = env.modular_assume_role_arn()
        if roles and self._expired():
            _LOG.info('Boto3 session inside ModularAssumeRoleClient descriptor '
                      'has expired. Re-assuming role')
            payloads = list(sts.assume_roles_default_payloads(roles))
            creds = sts.assume_roles_chain(payloads)
            self._update_session(**creds)
            self._client = None

        if not self._client:
            r = self._region_name or env.modular_aws_region() or env.aws_region()
            _LOG.info(f'Initializing {self._service_name} client within '
                      f'ModularAssumeRoleClient descriptor for region {r}')
            self._client = self.get_session().client(
                service_name=self._service_name,
                region_name=r,
            )
        return self._client
