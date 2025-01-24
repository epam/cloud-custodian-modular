import re
import uuid
from datetime import datetime, timedelta
from functools import cached_property
from time import time
from typing import Optional, TypedDict, List, Tuple, Generator

from botocore.exceptions import ClientError

from modular_sdk.commons.constants import MODULAR_AWS_ACCESS_KEY_ID_ENV, \
    MODULAR_AWS_SESSION_TOKEN_ENV, MODULAR_AWS_SECRET_ACCESS_KEY_ENV, \
    MODULAR_AWS_CREDENTIALS_EXPIRATION_ENV
from modular_sdk.commons.log_helper import get_logger
from modular_sdk.commons.time_helper import utc_datetime, utc_iso
from modular_sdk.services.aws_creds_provider import AWSCredentialsProvider
from modular_sdk.services.environment_service import EnvironmentService

_LOG = get_logger(__name__)


class StsService(AWSCredentialsProvider):
    class AssumeRoleResult(TypedDict):
        aws_access_key_id: str
        aws_secret_access_key: str
        aws_session_token: str
        expiration: datetime

    AssumeRolePayload = Tuple[str, Optional[str], Optional[int]]  # role arn, session_name, duration

    def __init__(self, environment_service: EnvironmentService,
                 aws_region, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        super(StsService, self).__init__(
            service_name='sts',
            aws_region=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token
        )
        self._environment_service = environment_service

    @staticmethod
    def generate_unique_session_name(name_body, suffix_length=6):
        suffix = str(uuid.uuid4())[-suffix_length:]
        return f'{name_body}-{suffix}'

    @cached_property
    def caller_identity(self):
        return self.client.get_caller_identity()

    @cached_property
    def role_arn_pattern(self) -> re.Pattern:
        return re.compile(r'^arn:aws:iam::\d{12}:role/[A-Za-z0-9_-]+$')

    def get_account_id(self) -> str:
        # _id = self._environment_service.account_id()
        # if not _id:
        #     _LOG.warning('Valid account id not found in envs. '
        #                  'Calling \'get_caller_identity\'')
        #     _id = self.get_caller_identity()['Account']
        return self.caller_identity['Account']

    def build_role_arn(self, maybe_arn: str,
                       account_id: Optional[str] = None) -> str:
        if self.is_role_arn(maybe_arn):
            return maybe_arn
        account_id = account_id or self.get_account_id()
        return f'arn:aws:iam::{account_id}:role/{maybe_arn}'

    def is_role_arn(self, arn: str) -> bool:
        return bool(re.match(self.role_arn_pattern, arn))

    def assume_role(self, role_arn, role_session_name,
                    duration=900) -> AssumeRoleResult:
        try:
            response = self.client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=role_session_name,
                DurationSeconds=duration
            )
        except ClientError as e:
            error_message = f'Error while assuming {role_arn}'
            _LOG.error(f'{error_message}: {e}')
            raise ConnectionAbortedError(error_message) from e
        credentials = response.get('Credentials')
        return {
            'aws_access_key_id': credentials.get('AccessKeyId'),
            'aws_secret_access_key': credentials.get('SecretAccessKey'),
            'aws_session_token': credentials.get('SessionToken'),
            'expiration': credentials.get('Expiration')  # datetime UTC
        }

    def assume_roles_chain(self, payloads: List[AssumeRolePayload]
                           ) -> AssumeRoleResult:
        """
        It assumes a chain of roles one after another.
        :param payloads:
        :return: AssumeRoleResult
        Returns the credentials and expiration of the last assumed role
        """
        assert payloads, 'At least one payload must be given'
        _sts = self.client
        for payload in payloads:
            assert len(payload) == 3, 'Invalid usage of the method'
            arn = payload[0]
            session_name = payload[1] or f'modular_sdk-sdk-session-{time()}'
            duration = payload[2] or 900
            try:
                _LOG.info(f'Assuming {arn} from chain')
                creds = _sts.assume_role(
                    RoleArn=arn,
                    RoleSessionName=session_name,
                    DurationSeconds=duration
                )['Credentials']
            except ClientError as e:
                error_message = f'Error while assuming {arn} from chain'
                _LOG.error(f'{error_message}: {e}')
                raise ConnectionAbortedError(error_message) from e
            _sts = AWSCredentialsProvider(
                service_name='sts',
                aws_region=self._region_name,
                aws_access_key_id=creds['AccessKeyId'],
                aws_secret_access_key=creds['SecretAccessKey'],
                aws_session_token=creds['SessionToken'],
            ).client
        # creds variable will exist, ignore warning
        return {
            'aws_access_key_id': creds.get('AccessKeyId'),
            'aws_secret_access_key': creds.get('SecretAccessKey'),
            'aws_session_token': creds.get('SessionToken'),
            'expiration': creds.get('Expiration')
        }

    def assume_roles_default_payloads(self, roles: List[str],
                                      session_name: Optional[str] = None,
                                      last_duration: Optional[int] = 3600
                                      ) -> Generator[AssumeRolePayload, None, None]:
        """
        Just to keep the same code in one place. We could have easily
        done without this method.
        This method puts session duration for the last payload. Additionally,
        it validated roles ARNs and skips one in case it's invalid. Session
        names are currently None because they do not matter
        :param session_name: name for each session. Current timestamp
         will be added.
        :param last_duration: session duration for the last payload
        :param roles:
        :return:
        """
        def session():
            return f'{session_name}-{time()}' if session_name else None

        n = len(roles)
        for i, role in enumerate(roles):
            if not self.is_role_arn(role):
                _LOG.warning(f'The string {roles} is not a role arn. '
                             f'Skipping it.')
                continue
            _dur = last_duration if i == (n - 1) else 900  # 900 the smallest
            yield role, session(), _dur

    def assure_modular_credentials_valid(self) -> bool:
        """
        If modular_sdk uses 'modular_assume_role_arn', it uses temp aws credentials
        to be able to interact with another AWS account. The creds
        expiration is kept in envs. They must be re-assumed periodically. So,
        this method checks whether the creds are about to expire and if
        they really are - re-assumes them.
        Returns True in case the role was re-assumed. Otherwise - False
        """
        roles = self._environment_service.modular_assume_role_arn()
        if not roles:
            return False
        ex = self._environment_service.modular_aws_credentials_expiration()
        in_a_while = utc_datetime() + timedelta(minutes=5)
        if not ex or in_a_while > utc_datetime(ex):
            _LOG.info(f'Role {roles[-1]} has not been assumed or has expired. '
                      f'Reassuming the chain: {roles}')
            creds = self.assume_roles_chain(
                list(self.assume_roles_default_payloads(roles))
            )
            _LOG.debug('Credentials received successfully. '
                       'Setting them to envs')
            ak, sk = creds['aws_access_key_id'], creds['aws_secret_access_key']
            st = creds['aws_session_token']
            self._environment_service.set(MODULAR_AWS_ACCESS_KEY_ID_ENV, ak)
            self._environment_service.set(MODULAR_AWS_SECRET_ACCESS_KEY_ENV, sk)
            self._environment_service.set(MODULAR_AWS_SESSION_TOKEN_ENV, st)
            self._environment_service.set(MODULAR_AWS_CREDENTIALS_EXPIRATION_ENV,
                                          utc_iso(creds['expiration']))
            return True
        else:
            return False
