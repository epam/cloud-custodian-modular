from typing import Optional, Iterator, List

from modular_sdk.commons import RESPONSE_BAD_REQUEST_CODE, \
    RESPONSE_RESOURCE_NOT_FOUND_CODE, generate_id, default_instance
from modular_sdk.commons.constants import AVAILABLE_APPLICATION_TYPES, \
    ApplicationType
from modular_sdk.commons.exception import ModularException
from modular_sdk.commons.log_helper import get_logger
from modular_sdk.commons.time_helper import utc_datetime
from modular_sdk.models.application import Application
from modular_sdk.modular import Modular
from modular_sdk.services.customer_service import CustomerService

_LOG = get_logger(__name__)


class ApplicationService:

    def __init__(self, customer_service: CustomerService):
        self.customer_service = customer_service

    def build(self, customer_id: str, type: str, description: str,
              created_by: str, application_id: Optional[str] = None,
              is_deleted=False, meta: Optional[dict] = None,
              secret: Optional[str] = None) -> Application:
        application_id = application_id or generate_id()
        if type not in AVAILABLE_APPLICATION_TYPES:
            _LOG.error(f'Invalid application type specified. Available '
                       f'options: \'{AVAILABLE_APPLICATION_TYPES}\'')
            raise ModularException(
                code=RESPONSE_BAD_REQUEST_CODE,
                content=f'Invalid application type specified. Available '
                        f'options: \'{AVAILABLE_APPLICATION_TYPES}\''
            )
        if not self.customer_service.get(name=customer_id):
            _LOG.error(f'Customer with name \'{customer_id}\' does not exist.')
            raise ModularException(
                code=RESPONSE_RESOURCE_NOT_FOUND_CODE,
                content=f'Customer with name \'{customer_id}\' does not exist.'
            )
        return Application(
            application_id=application_id,
            customer_id=customer_id,
            type=type.value if isinstance(type, ApplicationType) else type,
            description=description,
            is_deleted=is_deleted,
            meta=meta,
            secret=secret,
            created_by=created_by
        )

    @staticmethod
    def get_application_by_id(application_id) -> Optional[Application]:
        return Application.get_nullable(hash_key=application_id)

    @staticmethod
    def i_get_application_by_customer(
            customer_id: str, application_type: Optional[str] = None,
            deleted: Optional[bool] = None
    ) -> Iterator[Application]:

        condition = deleted if deleted is None else (
                Application.is_deleted == deleted
        )
        _type: str = default_instance(application_type, str)

        if _type:
            condition &= Application.type == _type

        return Application.customer_id_type_index.query(
            hash_key=customer_id, filter_condition=condition
        )

    @staticmethod
    def list(customer: Optional[str] = None, _type: Optional[str] = None,
             deleted: Optional[bool] = None,
             limit: Optional[int] = None) -> Iterator[Application]:
        condition = None
        if isinstance(deleted, bool):
            condition &= Application.is_deleted == deleted
        if isinstance(_type, str):
            condition &= Application.type == _type
        if customer:
            return Application.customer_id_type_index.query(
                hash_key=customer,
                filter_condition=condition,
                limit=limit
            )
        return Application.scan(filter_condition=condition, limit=limit)

    @staticmethod
    def save(application: Application):
        application.save()

    def update_meta(self, application: Application, updated_by: str):
        _LOG.debug(f'Going to update application {application.application_id}'
                   f'meta')

        self.update(
            application=application,
            attributes=[
                Application.meta
            ],
            updated_by=updated_by
        )
        _LOG.debug('Application meta was updated')

    @staticmethod
    def update(application: Application, attributes: List, updated_by: str):
        updatable_attributes = [
            Application.description,
            Application.meta,
            Application.secret,
            Application.updated_by,
            Application.is_deleted
        ]

        actions = []

        for attribute in attributes:
            if attribute not in updatable_attributes:
                _LOG.warning(f'Attribute {attribute.attr_name} '
                             f'can\'t be updated.')
                continue
            python_attr_name = Application._dynamo_to_python_attr(
                attribute.attr_name)
            update_value = getattr(application, python_attr_name)
            actions.append(attribute.set(update_value))

        actions.append(Application.updated_by.set(updated_by))
        actions.append(Application.update_timestamp.set(
            int(utc_datetime().timestamp() * 1e3)))

        application.update(actions=actions)

    @staticmethod
    def get_dto(application: Application) -> dict:
        return application.get_json()

    @staticmethod
    def mark_deleted(application: Application):
        _LOG.debug(f'Going to mark the application '
                   f'{application.application_id} as deleted')
        if application.is_deleted:
            _LOG.warning(f'Application \'{application.application_id}\' '
                         f'is already deleted.')
            return
        application.update(actions=[
            Application.is_deleted.set(True),
            Application.deletion_timestamp.set(utc_datetime().timestamp() * 1e3)
        ])
        _LOG.debug('Application was marked as deleted')

    @staticmethod
    def force_delete(application: Application):
        _LOG.debug(f'Going to delete application {application.application_id}')
        application.delete()
        _LOG.debug('Application has been deleted')
