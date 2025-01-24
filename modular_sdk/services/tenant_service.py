from typing import Optional, Iterator, Union, List
from http import HTTPStatus
from pynamodb.pagination import ResultIterator

from modular_sdk.commons import default_instance, deprecated
from modular_sdk.commons.constants import ALLOWED_TENANT_PARENT_MAP_KEYS
from modular_sdk.commons.exception import ModularException
from modular_sdk.commons.log_helper import get_logger
from modular_sdk.models.parent import Parent
from modular_sdk.models.tenant import Tenant

_LOG = get_logger(__name__)


class TenantService:
    @staticmethod
    def get(tenant_name: str,
            attributes_to_get: Optional[list] = None) -> Optional[Tenant]:
        return Tenant.get_nullable(
            hash_key=tenant_name,
            attributes_to_get=attributes_to_get
        )

    def does_exist(self, tenant_name: str,
                   is_active: Optional[bool] = None) -> bool:
        """
        Use this method only if you really don't need the tenant instance.
        Only if you need to know whether the tenant exists
        :param tenant_name:
        :param is_active: if None, this attribute is ignored. If bool,
        the tenant will be checked
        :return:
        """
        if isinstance(is_active, bool):
            item = self.get(tenant_name,
                            attributes_to_get=[Tenant.name, Tenant.is_active])
            return bool(item) and item.is_active == is_active
        # is_active == None
        return bool(self.get(tenant_name, attributes_to_get=[Tenant.name]))

    @staticmethod
    def scan_tenants(only_active=False, limit: int = None,
                     last_evaluated_key: Union[dict, str] = None):
        return list(TenantService.i_scan_tenants(
            only_active, limit, last_evaluated_key))

    @staticmethod
    def i_scan_tenants(only_active=False, limit: int = None,
                       last_evaluated_key: Union[dict, str] = None):
        condition = None
        if only_active:
            condition &= Tenant.is_active == True
        return Tenant.scan(limit=limit, last_evaluated_key=last_evaluated_key,
                           filter_condition=condition)

    @classmethod
    @deprecated('Logic is deprecated')
    def get_tenants_by_parent_id(cls, parent_id, only_active=True):
        return list(cls.i_get_tenant_by_parent_id(parent_id, only_active))

    @staticmethod
    @deprecated('Logic is deprecated')
    def i_get_tenant_by_parent_id(parent_id: str,
                                  active: Optional[bool] = None,
                                  limit: Optional[int] = None,
                                  last_evaluated_key: Optional[dict] = None
                                  ) -> Iterator[Tenant]:
        """
        TODO management parent id is not the only one parent id within
        a tenant. What about others?
        """
        condition = active if active is None else (Tenant.is_active == active)
        if condition is not None:
            condition &= Tenant.management_parent_id == parent_id

        return Tenant.scan(
            filter_condition=condition,
            limit=limit,
            last_evaluated_key=last_evaluated_key
        )

    @staticmethod
    def i_get_tenant_by_customer(
            customer_id: str, active: Optional[bool] = None,
            tenant_name: Optional[str] = None, limit: int = None,
            last_evaluated_key: Union[dict, str] = None,
            cloud: Optional[str] = None,
            attributes_to_get: Optional[list] = None,
            rate_limit: Optional[int] = None
    ) -> ResultIterator:

        condition = active if active is None else (Tenant.is_active == active)
        name = default_instance(tenant_name, str)

        if condition is not None and name:
            condition &= Tenant.name == name
        elif name:
            condition = Tenant.name == name

        if condition is not None and cloud:
            condition &= Tenant.cloud == cloud
        elif cloud:
            condition = Tenant.cloud == cloud

        return Tenant.customer_name_index.query(
            hash_key=customer_id, filter_condition=condition, limit=limit,
            last_evaluated_key=last_evaluated_key,
            attributes_to_get=attributes_to_get,
            rate_limit=rate_limit
        )

    @staticmethod
    def i_get_by_acc(acc: str, active: Optional[bool] = None,
                     limit: int = None,
                     last_evaluated_key: Union[dict, str] = None,
                     attributes_to_get: List[str] = None):
        condition = active if active is None else (Tenant.is_active == active)
        return Tenant.project_index.query(
            hash_key=acc, filter_condition=condition, limit=limit,
            last_evaluated_key=last_evaluated_key,
            attributes_to_get=attributes_to_get
        )

    @staticmethod
    def i_get_by_dntl(
            dntl: str, cloud: str = None, active: Optional[bool] = None,
            limit: int = None, last_evaluated_key: Union[dict, str] = None,
            attributes_to_get: List[str] = None
    ):
        fc = None if active is None else (Tenant.is_active == active)
        rc = None if cloud is None else (Tenant.cloud == cloud.upper())
        return Tenant.dntl_c_index.query(
            hash_key=dntl, range_key_condition=rc, filter_condition=fc,
            limit=limit, last_evaluated_key=last_evaluated_key,
            attributes_to_get=attributes_to_get
        )

    @staticmethod
    @deprecated('Use i_get_by_acc instead')
    def i_get_by_accN(accN: str, active: Optional[bool] = None,
                      limit: int = None,
                      last_evaluated_key: Union[dict, str] = None,
                      attributes_to_get: List[str] = None):
        fc = None if active is None else (Tenant.is_active == active)
        return Tenant.project_index.query(
            hash_key=accN, filter_condition=fc,
            limit=limit, last_evaluated_key=last_evaluated_key,
            attributes_to_get=attributes_to_get
        )

    @staticmethod
    def add_to_parent_map(tenant: Tenant, parent: Parent,
                          type_: str) -> Tenant:
        if type_ not in ALLOWED_TENANT_PARENT_MAP_KEYS:
            _LOG.warning(f'Unsupported type \'{type_}\'. Available options: '
                         f'{", ".join(ALLOWED_TENANT_PARENT_MAP_KEYS)}')
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'Unsupported type \'{type_}\'. Available options: '
                        f'{", ".join(ALLOWED_TENANT_PARENT_MAP_KEYS)}'
            )
        if not tenant.is_active:
            _LOG.warning(f'Tenant \'{tenant.name}\' is not active.')
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'Tenant \'{tenant.name}\' is not active.'
            )
        if parent.is_deleted:
            _LOG.warning(f'Parent \'{parent.parent_id}\' is deleted.')
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'Tenant \'{tenant.name}\' is deleted.'
            )
        parent_map = tenant.parent_map.as_dict()  # default "dict"
        if type_ in parent_map:
            _LOG.warning(f'Tenant \'{tenant.name}\' already has \'{type_}\' '
                         f'linkage type.')
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f'Tenant \'{tenant.name}\' already has \'{type_}\' '
                        f'linkage type.'
            )
        # we can update just one attribute only in
        # case the map already exists in DB. Otherwise -> ValidationException
        parent_map[type_] = parent.parent_id
        tenant.update(actions=[
            Tenant.parent_map.set(parent_map)
        ])
        return tenant  # no need to return

    @staticmethod
    def remove_from_parent_map(tenant: Tenant, type_) -> Tenant:
        if not tenant.is_active:
            _LOG.warning(f'Tenant \'{tenant.name}\' is not active.')
            return tenant
        tenant.update(actions=[
            Tenant.parent_map[type_].remove()
        ])
        return tenant

    @staticmethod
    def get_dto(tenant: Tenant):
        """Be CAREFUL: returns both active and inactive regions"""
        tenant_json = tenant.get_json()
        regions = tenant_json.get('regions') or []
        tenant_json['account_id'] = tenant_json.pop('project', None)
        tenant_json['regions'] = [
            each['maestro_name'] for each in regions if 'maestro_name' in each
        ]
        return tenant_json
