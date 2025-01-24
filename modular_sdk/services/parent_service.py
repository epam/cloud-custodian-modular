from typing import Optional, Iterator, Union, List
from http import HTTPStatus

from pynamodb.expressions.condition import Condition
from datetime import datetime
from modular_sdk.commons import generate_id
from modular_sdk.commons.constants import ALL_PARENT_TYPES, ParentScope, \
    COMPOUND_KEYS_SEPARATOR, CLOUD_PROVIDERS, ParentType
from modular_sdk.commons.exception import ModularException
from modular_sdk.commons.log_helper import get_logger
from modular_sdk.commons.time_helper import java_timestamp, utc_datetime
from modular_sdk.commons.time_helper import utc_iso
from modular_sdk.models.parent import Parent
from modular_sdk.models.tenant import Tenant
from modular_sdk.services.customer_service import CustomerService
from modular_sdk.services.tenant_service import TenantService

_LOG = get_logger(__name__)


class ParentService:

    def __init__(self, tenant_service: TenantService,
                 customer_service: CustomerService):
        self.customer_service = customer_service
        self.tenant_service = tenant_service

    @staticmethod
    def get_parent_by_id(parent_id: str) -> Optional[Parent]:
        return Parent.get_nullable(hash_key=parent_id)

    @staticmethod
    def list():
        # todo do not use it
        return list(Parent.scan())

    @staticmethod
    def list_application_parents(application_id, only_active=True):
        return list(ParentService.i_list_application_parents(
            application_id=application_id, only_active=only_active
        ))

    @staticmethod
    def i_list_application_parents(application_id: str, 
                                   type_: Optional[ParentType] = None,
                                   scope: Optional[ParentScope] = None,
                                   tenant_or_cloud: Optional[str] = None,
                                   by_prefix: Optional[bool] = False,
                                   only_active=True,
                                   limit: Optional[int] = None,
                                   last_evaluated_key: Optional[dict] = None,
                                   rate_limit: Optional[int] = None
                                   ) -> Iterator[Parent]:

        # can be an empty string is we want to retrieve with literally '' cloud
        is_tenant_or_cloud = isinstance(tenant_or_cloud, str)
        if is_tenant_or_cloud and not scope or scope and not type_:
            raise AssertionError('invalid usage')

        if type_ and scope and is_tenant_or_cloud:
            key = COMPOUND_KEYS_SEPARATOR.join((type_, scope, tenant_or_cloud))
            if by_prefix:
                rkc = Parent.type_scope.startswith(key)
            else:
                rkc = (Parent.type_scope == key)
        elif type_ and scope:
            rkc = Parent.type_scope.startswith(COMPOUND_KEYS_SEPARATOR.join((
                type_, scope, ''
            )))
        elif type_:
            rkc = Parent.type_scope.startswith(
                f'{type_}{COMPOUND_KEYS_SEPARATOR}')
        else:
            rkc = None
        if only_active:
            rkc &= (Parent.is_deleted == False)

        return Parent.application_id_index.query(
            hash_key=application_id,
            filter_condition=rkc,
            limit=limit,
            last_evaluated_key=last_evaluated_key,
            rate_limit=rate_limit
        )

    def i_get_parent_by_customer(self, customer_id: str,
                                 parent_type: Optional[Union[ParentType, List[ParentType]]] = None,  # noqa
                                 is_deleted: Optional[bool] = None,
                                 meta_conditions: Optional[Condition] = None,
                                 limit: Optional[int] = None,
                                 last_evaluated_key: Optional[dict] = None
                                 ) -> Iterator[Parent]:
        """
        Meta conditions can be used like this:
        parent = next(parent_service.i_get_parent_by_customer(
            customer_id='EPAM Systems',
            parent_type='CUSTODIAN',
            is_deleted=False,
            meta_conditions=(Parent.meta['key'] == 'value'),
            limit=1
        ), None)
        :param customer_id:
        :param parent_type:
        :param is_deleted:
        :param meta_conditions:
        :param limit:
        :param last_evaluated_key:
        :return:
        """
        condition = meta_conditions
        rkc = None
        if isinstance(parent_type, list):
            condition &= (Parent.type.is_in(*parent_type))
        elif parent_type:  # enum value or str
            rkc = Parent.type_scope.startswith(
                self.build_type_scope(parent_type)
            )
        if isinstance(is_deleted, bool):
            condition &= (Parent.is_deleted == is_deleted)
        return Parent.customer_id_scope_index.query(
            hash_key=customer_id,
            range_key_condition=rkc,
            filter_condition=condition,
            limit=limit,
            last_evaluated_key=last_evaluated_key
        )

    def build(self, application_id: str, customer_id: str,
              parent_type: ParentType, created_by: str,
              is_deleted: bool = False, description: Optional[str] = None,
              meta: Optional[dict] = None,
              scope: Optional[ParentScope] = None,
              tenant_name: Optional[str] = None,
              cloud: Optional[str] = None) -> Parent:
        """
        Make sure to provide valid scope, tenant_name and cloud. Or
        use specific methods: create_all_scope, create_tenant_scope
        :param application_id:
        :param customer_id:
        :param parent_type:
        :param is_deleted:
        :param description:
        :param meta:
        :param scope:
        :param tenant_name:
        :param cloud:
        :param created_by:
        :return:
        """
        # TODO either move validation from here to outside or make the
        #  validation decent (what if application by id does not exist,
        #  what if meta for this parent_type is not valid?, ...)
        if parent_type not in ALL_PARENT_TYPES:
            _LOG.warning(f'Invalid parent type specified \'{parent_type}\'. '
                         f'Available options: {ALL_PARENT_TYPES}')
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'Invalid parent type specified \'{parent_type}\'. '
                        f'Available options are: {ALL_PARENT_TYPES}'
            )
        customer = self.customer_service.get(name=customer_id)
        if not customer:
            _LOG.error(f'Customer with name \'{customer_id}\' does not exist')
            raise ModularException(
                code=HTTPStatus.NOT_FOUND.value,
                content=f'Customer with name \'{customer_id}\' does not exist'
            )
        return self._create(
            customer_id=customer_id,
            application_id=application_id,
            type_=parent_type,
            description=description,
            meta=meta,
            is_deleted=is_deleted,
            scope=scope,
            tenant_name=tenant_name,
            cloud=cloud,
            created_by=created_by
        )

    @staticmethod
    def get_dto(parent: Parent) -> dict:
        dct = parent.get_json()
        ct = dct.pop('creation_timestamp', None)
        if ct:
            dct['created_at'] = utc_iso(datetime.fromtimestamp(ct / 1e3))
        dct.pop('type_scope', None)
        dct['scope'] = parent.scope
        if parent.cloud:
            dct['cloud'] = parent.cloud
        if parent.tenant_name:
            dct['tenant_name'] = parent.tenant_name
        return dct

    @staticmethod
    def save(parent: Parent):
        parent.save()

    def update_meta(self, parent: Parent, updated_by: str):
        _LOG.debug(f'Going to update parent {parent.parent_id} meta')

        self.update(
            parent=parent,
            attributes=[
                Parent.meta
            ],
            updated_by=updated_by
        )
        _LOG.debug('Parent meta was updated')

    @staticmethod
    def update(parent: Parent, attributes: List, updated_by: str):
        updatable_attributes = [
            Parent.description,
            Parent.meta,
            Parent.type,
            Parent.updated_by,
            Parent.is_deleted,
            Parent.type_scope
        ]

        actions = []

        for attribute in attributes:
            if attribute not in updatable_attributes:
                _LOG.warning(f'Attribute {attribute.attr_name} '
                             f'can\'t be updated.')
                continue
            python_attr_name = Parent._dynamo_to_python_attr(
                attribute.attr_name)
            update_value = getattr(parent, python_attr_name)
            actions.append(attribute.set(update_value))

        actions.append(Parent.updated_by.set(updated_by))
        actions.append(
            Parent.update_timestamp.set(int(utc_datetime().timestamp() * 1e3)))

        parent.update(actions=actions)

    @staticmethod
    def mark_deleted(parent: Parent):
        """
        Updates the item in DB! No need to save afterwards
        :param parent:
        :return:
        """
        _LOG.debug(f'Going to mark the parent {parent.parent_id} as deleted')
        if parent.is_deleted:
            _LOG.warning(f'Parent \'{parent.parent_id}\' is already deleted.')
            return

        parent.update(actions=[
            Parent.is_deleted.set(True),
            Parent.deletion_timestamp.set(int(utc_datetime().timestamp() * 1e3))
        ])
        _LOG.debug('Parent was marked as deleted')

    @staticmethod
    def force_delete(parent: Parent):
        _LOG.debug(f'Going to delete parent {parent.parent_id}')
        parent.delete()
        _LOG.debug('Parent has been deleted')

    # new methods
    @staticmethod
    def build_type_scope(type_: ParentType, scope: Optional[ParentScope] = None,
                         tenant_name: Optional[str] = None,
                         cloud: Optional[str] = None) -> str:
        """
        All asserts here are against developer errors
        :param type_:
        :param scope:
        :param tenant_name:
        :param cloud:
        :return:
        """
        scope = scope or ''
        tenant_name = tenant_name or ''
        cloud = (cloud or '').upper()
        # assert type_ in ALL_PARENT_TYPES, f'Invalid parent type {type_}'
        if not scope:
            _LOG.debug('Scope was not provided to build_type_scope. '
                       'Keeping tenant and cloud empty')
            return COMPOUND_KEYS_SEPARATOR.join((type_, scope, ''))
        if cloud:
            assert cloud in CLOUD_PROVIDERS, f'Invalid cloud: {cloud}'
        if scope == ParentScope.ALL:
            return COMPOUND_KEYS_SEPARATOR.join((type_, scope, cloud))
        # scope in (ParentScope.DISABLED, ParentScope.SPECIFIC)
        return COMPOUND_KEYS_SEPARATOR.join((type_, scope, tenant_name))

    def _create(self, customer_id: str, application_id: str, type_: ParentType,
                created_by: str, description: Optional[str] = None,
                meta: Optional[dict] = None, is_deleted: bool = False,
                scope: Optional[ParentScope] = None,
                tenant_name: Optional[str] = '',
                cloud: Optional[str] = '') -> Parent:
        """
        Raw create without excessive validations
        :param customer_id:
        :param application_id:
        :param type_:
        :param description:
        :param meta:
        :param is_deleted:
        :param scope:
        :param tenant_name:
        :param cloud:
        :param created_by:
        :return:
        """
        return Parent(
            parent_id=generate_id(),
            customer_id=customer_id,
            application_id=application_id,
            type=type_.value if isinstance(type_, ParentType) else type_,
            created_by=created_by,
            description=description,
            meta=meta if isinstance(meta, dict) else {},
            is_deleted=is_deleted,
            creation_timestamp=int(java_timestamp()),
            type_scope=self.build_type_scope(type_, scope, tenant_name, cloud)
        )

    def create_all_scope(self, application_id: str,
                         customer_id: str, type_: ParentType, created_by: str,
                         is_deleted: bool = False,
                         description: Optional[str] = None,
                         meta: Optional[dict] = None,
                         cloud: Optional[str] = None) -> Parent:
        return self._create(
            application_id=application_id,
            customer_id=customer_id,
            type_=type_,
            is_deleted=is_deleted,
            description=description,
            meta=meta,
            scope=ParentScope.ALL,
            cloud=cloud,
            created_by=created_by
        )

    def create_tenant_scope(self, application_id: str,
                            customer_id: str, type_: ParentType,
                            tenant_name: str,  created_by: str,
                            disabled: bool = False,
                            is_deleted: bool = False,
                            description: Optional[str] = None,
                            meta: Optional[dict] = None) -> Parent:
        return self._create(
            application_id=application_id,
            customer_id=customer_id,
            type_=type_,
            is_deleted=is_deleted,
            description=description,
            meta=meta,
            scope=ParentScope.DISABLED if disabled else ParentScope.SPECIFIC,
            tenant_name=tenant_name,
            created_by=created_by
        )

    def query_by_scope_index(self, customer_id: str,
                             type_: Optional[ParentType] = None,
                             scope: Optional[ParentScope] = None,
                             tenant_or_cloud: Optional[str] = None,
                             by_prefix: Optional[bool] = False,
                             is_deleted: Optional[bool] = False,
                             limit: Optional[int] = None,
                             last_evaluated_key: Optional[dict] = None,
                             ascending: Optional[bool] = True
                             ) -> Iterator[Parent]:
        """
        Low-level query method
        :param customer_id:
        :param type_:
        :param scope:
        :param tenant_or_cloud:
        :param by_prefix:
        :param is_deleted:
        :param limit:
        :param last_evaluated_key:
        :param ascending:
        :return:
        """
        # can be an empty string is we want to retrieve with literally '' cloud
        is_tenant_or_cloud = isinstance(tenant_or_cloud, str)
        if is_tenant_or_cloud and not scope or scope and not type_:
            raise AssertionError('invalid usage')

        if type_ and scope and is_tenant_or_cloud:
            key = COMPOUND_KEYS_SEPARATOR.join((type_, scope, tenant_or_cloud))
            if by_prefix:
                rkc = Parent.type_scope.startswith(key)
            else:
                rkc = (Parent.type_scope == key)
        elif type_ and scope:
            rkc = Parent.type_scope.startswith(COMPOUND_KEYS_SEPARATOR.join((
                type_, scope, ''
            )))
        elif type_:
            rkc = Parent.type_scope.startswith(
                f'{type_}{COMPOUND_KEYS_SEPARATOR}')
        else:
            rkc = None
        fc = None
        if isinstance(is_deleted, bool):
            fc = (Parent.is_deleted == is_deleted)
        return Parent.customer_id_scope_index.query(
            hash_key=customer_id,
            range_key_condition=rkc,
            limit=limit,
            last_evaluated_key=last_evaluated_key,
            scan_index_forward=ascending,
            filter_condition=fc
        )

    def get_by_tenant_scope(self, customer_id: str, type_: ParentType,
                            tenant_name: Optional[str] = None,
                            disabled: bool = False,
                            limit: Optional[int] = None,
                            last_evaluated_key: Optional[dict] = None,
                            ascending: bool = True) -> Iterator[Parent]:
        return self.query_by_scope_index(
            customer_id=customer_id,
            type_=type_,
            scope=ParentScope.DISABLED if disabled else ParentScope.SPECIFIC,
            tenant_or_cloud=tenant_name,
            by_prefix=False,
            limit=limit,
            last_evaluated_key=last_evaluated_key,
            ascending=ascending
        )

    def get_by_all_scope(self, customer_id: str, type_: ParentType,
                         cloud: Optional[str] = None,
                         limit: Optional[int] = None,
                         last_evaluated_key: Optional[dict] = None,
                         ascending: bool = True) -> Iterator[Parent]:
        # todo allow with empty cloud
        return self.query_by_scope_index(
            customer_id=customer_id,
            type_=type_,
            scope=ParentScope.ALL,
            tenant_or_cloud=cloud,
            by_prefix=False,
            limit=limit,
            last_evaluated_key=last_evaluated_key,
            ascending=ascending
        )

    def get_linked_parent_by_tenant(self, tenant: Tenant, type_: ParentType
                                    ) -> Optional[Parent]:
        return self.get_linked_parent(
            tenant_name=tenant.name,
            cloud=tenant.cloud,
            customer_name=tenant.customer_name,
            type_=type_
        )

    def get_linked_parent(self, tenant_name: str, cloud: Optional[str],
                          customer_name: str,
                          type_: ParentType) -> Optional[Parent]:
        """

        :param tenant_name:
        :param cloud:
        :param customer_name:
        :param type_:
        :return:
        """
        _LOG.debug(f'Looking for a disabled parent with type {type_} for '
                   f'tenant {tenant_name}')
        disabled = next(self.get_by_tenant_scope(
            customer_id=customer_name,
            type_=type_,
            tenant_name=tenant_name,
            disabled=True,
            limit=1
        ), None)
        if disabled:
            _LOG.info('Disabled parent is found. Returning None')
            return
        _LOG.debug(f'Looking for a specific parent with type {type_} for '
                   f'tenant {tenant_name}')
        specific = next(self.get_by_tenant_scope(
            customer_id=customer_name,
            type_=type_,
            tenant_name=tenant_name,
            disabled=False,
            limit=1
        ), None)
        if specific:
            _LOG.info('Specific parent is found. Returning it')
            return specific
        if cloud:
            _LOG.debug(f'Looking for a parent with scope ALL and type {type_} '
                       f'for tenant\'s cloud')
            all_cloud = next(self.get_by_all_scope(
                customer_id=customer_name,
                type_=type_,
                cloud=cloud.upper()
            ), None)
            if all_cloud:
                _LOG.info('Parent with type ALL and tenant\'s cloud found.')
                return all_cloud
        all_ = next(self.get_by_all_scope(
            customer_id=customer_name,
            type_=type_,
        ), None)
        if all_:
            _LOG.info('Parent with type ALL found.')
            return all_
        _LOG.info(f'No parent with type {type_} for '
                  f'tenant {tenant_name} found')
