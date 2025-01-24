import os

from modular_sdk.commons import validate_params, SingletonMeta
from modular_sdk.commons.time_helper import utc_iso
from modular_sdk.commons.constants import SERVICE_MODE_DOCKER, \
    MODULAR_SERVICE_MODE_ENV, \
    PARAM_MONGO_DB_NAME, PARAM_MONGO_URL, PARAM_MONGO_PASSWORD, \
    PARAM_MONGO_USER, PARAM_ASSUME_ROLE_ARN, SERVICE_MODE_SAAS, \
    ASSUMES_ROLE_SESSION_NAME, MODULAR_AWS_ACCESS_KEY_ID_ENV, \
    MODULAR_AWS_SECRET_ACCESS_KEY_ENV, MODULAR_AWS_SESSION_TOKEN_ENV, \
    MODULAR_AWS_CREDENTIALS_EXPIRATION_ENV
from modular_sdk.services.impl.maestro_http_transport_service import \
    MaestroHTTPConfig


class Modular(metaclass=SingletonMeta):
    # services
    __rabbit_conn = None
    __environment_service = None
    __customer_service = None
    __application_service = None
    __parent_service = None
    __region_service = None
    __tenant_service = None
    __tenant_settings_service = None
    __customer_settings_service = None
    __sts_service = None
    __sqs_service = None
    __lambda_service = None
    __events_service = None
    __rabbit_transport_service = None
    __http_transport_service = None
    __settings_service = None
    __instantiated_setting_group = []
    __credentials_service = None
    __thread_local_storage_service = None

    __ssm_service = None
    __assume_role_ssm_service = None

    def __init__(self, *args, **kwargs):
        kwargs = self.__collect_kwargs(kwargs)

        service_mode = kwargs.get(MODULAR_SERVICE_MODE_ENV, SERVICE_MODE_SAAS)
        assume_role_arn = kwargs.get(
            PARAM_ASSUME_ROLE_ARN)
        if service_mode == SERVICE_MODE_SAAS and assume_role_arn:
            sts_service = self.sts_service()
            assumed_credentials = sts_service.assume_roles_chain(
                list(sts_service.assume_roles_default_payloads(
                    assume_role_arn.split(','),
                    ASSUMES_ROLE_SESSION_NAME
                ))
            )
            os.environ[MODULAR_AWS_ACCESS_KEY_ID_ENV] = assumed_credentials[
                'aws_access_key_id']
            os.environ[MODULAR_AWS_SECRET_ACCESS_KEY_ENV] = \
                assumed_credentials['aws_secret_access_key']
            os.environ[MODULAR_AWS_SESSION_TOKEN_ENV] = assumed_credentials[
                'aws_session_token']
            os.environ[MODULAR_AWS_CREDENTIALS_EXPIRATION_ENV] = \
                utc_iso(assumed_credentials['expiration'])
            os.environ[PARAM_ASSUME_ROLE_ARN] = assume_role_arn
        elif service_mode == SERVICE_MODE_DOCKER:
            required_mongodb_attrs = (
                MODULAR_SERVICE_MODE_ENV, PARAM_MONGO_USER, PARAM_MONGO_PASSWORD,
                PARAM_MONGO_URL, PARAM_MONGO_DB_NAME)
            validate_params(kwargs, required_mongodb_attrs)

            for attr in required_mongodb_attrs:
                os.environ[attr] = kwargs.get(attr)

    @staticmethod
    def __collect_kwargs(kwargs):
        """
        PARAM_ASSUME_ROLE_ARN is string, but it can contain multiple
        roles divided by ',', hence:
        TODO, in case kwargs are given, we should expect
         modular_assume_role_arn to be a list. Or, better, use
         environment_service here instead of os.environ. ES already
         converts values.
        :param kwargs:
        :return:
        """
        allowed_attrs = (
            MODULAR_SERVICE_MODE_ENV, PARAM_MONGO_USER, PARAM_MONGO_PASSWORD,
            PARAM_MONGO_URL, PARAM_MONGO_DB_NAME, PARAM_ASSUME_ROLE_ARN)
        kwargs = {k: v for k, v in kwargs.items() if k in allowed_attrs}

        for attr in allowed_attrs:
            if attr not in kwargs and attr in os.environ:
                kwargs[attr] = os.environ.get(attr)
        if not kwargs.get(MODULAR_SERVICE_MODE_ENV):
            kwargs[MODULAR_SERVICE_MODE_ENV] = SERVICE_MODE_SAAS
        return kwargs

    def __str__(self):
        return str(id(self))

    def environment_service(self):
        if not self.__environment_service:
            from modular_sdk.services.environment_service import \
                EnvironmentService
            self.__environment_service = EnvironmentService()
        return self.__environment_service

    def application_service(self):
        if not self.__application_service:
            from modular_sdk.services.application_service import \
                ApplicationService
            self.__application_service = ApplicationService(
                customer_service=self.customer_service()
            )
        return self.__application_service

    def customer_service(self):
        if not self.__customer_service:
            from modular_sdk.services.customer_service import CustomerService
            self.__customer_service = CustomerService()
        return self.__customer_service

    def parent_service(self):
        if not self.__parent_service:
            from modular_sdk.services.parent_service import ParentService
            self.__parent_service = ParentService(
                tenant_service=self.tenant_service(),
                customer_service=self.customer_service()
            )
        return self.__parent_service

    def region_service(self):
        if not self.__region_service:
            from modular_sdk.services.region_service import RegionService
            self.__region_service = RegionService(
                tenant_service=self.tenant_service()
            )
        return self.__region_service

    def tenant_service(self):
        if not self.__tenant_service:
            from modular_sdk.services.tenant_service import TenantService
            self.__tenant_service = TenantService()
        return self.__tenant_service

    def tenant_settings_service(self):
        if not self.__tenant_settings_service:
            from modular_sdk.services.tenant_settings_service import \
                TenantSettingsService
            self.__tenant_settings_service = TenantSettingsService()
        return self.__tenant_settings_service

    def customer_settings_service(self):
        if not self.__customer_settings_service:
            from modular_sdk.services.customer_settings_service import \
                CustomerSettingsService
            self.__customer_settings_service = CustomerSettingsService()
        return self.__customer_settings_service

    def sts_service(self):
        if not self.__sts_service:
            from modular_sdk.services.sts_service import StsService
            self.__sts_service = StsService(
                environment_service=self.environment_service(),
                aws_region=self.environment_service().aws_region())
        return self.__sts_service

    def sqs_service(self):
        if not self.__sqs_service:
            from modular_sdk.services.sqs_service import SQSService
            self.__sqs_service = SQSService(
                aws_region=self.environment_service().aws_region(),
                environment_service=self.environment_service()
            )
        return self.__sqs_service

    def lambda_service(self):
        if not self.__lambda_service:
            from modular_sdk.services.lambda_service import LambdaService
            self.__lambda_service = LambdaService(
                aws_region=self.environment_service().aws_region())
        return self.__lambda_service

    def events_service(self):
        if not self.__events_service:
            from modular_sdk.services.events_service import EventsService
            self.__events_service = EventsService(
                aws_region=self.environment_service().aws_region())
        return self.__events_service

    def rabbit(self, connection_url, timeout=None, refresh=False):
        if not self.__rabbit_conn or refresh:
            from modular_sdk.connections.rabbit_connection import \
                RabbitMqConnection
            self.__rabbit_conn = RabbitMqConnection(
                connection_url=connection_url,
                timeout=timeout
            )
        return self.__rabbit_conn

    def rabbit_transport_service(self, connection_url, config,
                                 timeout=None):
        if not self.__rabbit_transport_service:
            from modular_sdk.services.impl.maestro_rabbit_transport_service import \
                MaestroRabbitMQTransport
            rabbit_connection = self.rabbit(
                connection_url=connection_url,
                timeout=timeout,
                refresh=True
            )
            self.__rabbit_transport_service = MaestroRabbitMQTransport(
                rabbit_connection=rabbit_connection,
                config=config
            )
        return self.__rabbit_transport_service

    def http_transport_service(
            self,
            api_link: str,
            config: MaestroHTTPConfig,
            timeout: int | None = None,
    ):
        if not self.__http_transport_service:
            from modular_sdk.services.impl.maestro_http_transport_service import \
                MaestroHTTPTransport
            self.__http_transport_service = MaestroHTTPTransport(
                config=config, api_link=api_link, timeout=timeout,
            )
        return self.__http_transport_service

    def settings_service(self, group_name):
        if not self.__settings_service or \
                group_name not in self.__instantiated_setting_group:
            from modular_sdk.services.settings_management_service import \
                SettingsManagementService
            self.__settings_service = SettingsManagementService(
                group_name=group_name
            )
        return self.__settings_service

    def ssm_service(self):
        if not self.__ssm_service:
            from modular_sdk.services.ssm_service import VaultSSMClient, \
                SSMService, SSMClientCachingWrapper
            if self.environment_service().is_docker():
                self.__ssm_service = VaultSSMClient()
            else:
                self.__ssm_service = SSMService(
                    aws_region=self.environment_service().aws_region()
                )
            self.__ssm_service = SSMClientCachingWrapper(
                client=self.__ssm_service,
                environment_service=self.environment_service()
            )
        return self.__ssm_service

    def assume_role_ssm_service(self):
        if not self.__assume_role_ssm_service:
            from modular_sdk.services.ssm_service import VaultSSMClient, \
                ModularAssumeRoleSSMService, SSMClientCachingWrapper
            if self.environment_service().is_docker():
                self.__assume_role_ssm_service = VaultSSMClient()
            else:
                self.__assume_role_ssm_service = ModularAssumeRoleSSMService()
            self.__assume_role_ssm_service = SSMClientCachingWrapper(
                client=self.__assume_role_ssm_service,
                environment_service=self.environment_service()
            )
        return self.__assume_role_ssm_service

    def maestro_credentials_service(self):
        if not self.__credentials_service:
            from modular_sdk.services.impl.maestro_credentials_service import \
                MaestroCredentialsService
            self.__credentials_service = \
                MaestroCredentialsService.build()
        return self.__credentials_service

    def thread_local_storage_service(self):
        if not self.__thread_local_storage_service:
            from modular_sdk.services.thread_local_storage_service \
                import ThreadLocalStorageService
            self.__thread_local_storage_service = ThreadLocalStorageService()
        return self.__thread_local_storage_service

    def reset(self, service: str):
        """Removes the saved instance of the service. It is useful,
        for example, in case of gitlab service - when we want to use
        different rule-sources configurations"""
        private_service_name = f'_MODULAR__{service}'
        if not hasattr(self, private_service_name):
            raise AssertionError(
                f'In case you are using this method, make sure your '
                f'service {private_service_name} exists amongst the '
                f'private attributes')
        setattr(self, private_service_name, None)
