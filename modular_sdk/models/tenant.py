from typing import Optional

from pynamodb.attributes import (UnicodeAttribute, ListAttribute, MapAttribute)
from pynamodb.indexes import AllProjection
from pynamodb.indexes import GlobalSecondaryIndex
from modular_sdk.models.pynamongo.models import ModularBaseModel


from modular_sdk.commons.constants import ALLOWED_TENANT_PARENT_MAP_KEYS
from modular_sdk.models.base_meta import BaseMeta, TABLES_PREFIX
from modular_sdk.models.region import RegionAttr
from modular_sdk.models.pynamongo.attributes import M3BooleanAttribute

TENANT_NAME = 'n'
MANAGEMENT_PARENT_ID = 'mpid'
DISPLAY_NAME = 'dn'
ACTIVATION_DATE = 'ad'
DEACTIVATION_DATE = 'dd'

DNTL_NAME_KEY = 'dntl'
GENERAL_PROJECT_ID = 'acc'
PRIMARY_CONTACTS = 'pc'
SECONDARY_CONTACTS = 'sc'
TENANT_MANAGER = 'tmc'
DEFAULT_INSTANCE_OWNER = 'do'
TENANT_CONTACT = 'ct'

REGIONS = 'r'

READ_ONLY = 'ro'
IS_ACTIVE = 'act'
CUSTOMER_NAME = 'ctmr'
CLOUD = 'c'
PARENT_MAP = 'pid'

MODULAR_TENANTS_TABLE_NAME = 'Tenants'


class Contacts(MapAttribute):
    primary_contacts = ListAttribute(attr_name=PRIMARY_CONTACTS, null=True)
    secondary_contacts = ListAttribute(attr_name=SECONDARY_CONTACTS, null=True)
    tenant_manager_contacts = ListAttribute(attr_name=TENANT_MANAGER,
                                            null=True)
    default_owner = UnicodeAttribute(attr_name=DEFAULT_INSTANCE_OWNER,
                                     null=True)


class DisplayNameToLowerCloudIndex(GlobalSecondaryIndex):
    """
    This class represents a Tenant display name + Cloud global secondary index
    """

    class Meta(BaseMeta):
        index_name = 'dntl-c-index'
        read_capacity_units = 1
        write_capacity_units = 1
        projection = AllProjection()

    display_name_to_lower = UnicodeAttribute(attr_name=DNTL_NAME_KEY,
                                             hash_key=True)
    cloud = UnicodeAttribute(attr_name=CLOUD, range_key=True)


class ProjectIndex(GlobalSecondaryIndex):
    """
    This class represents a Project global secondary index
    """

    class Meta(BaseMeta):
        index_name = 'ac-index'
        read_capacity_units = 1
        write_capacity_units = 1
        projection = AllProjection()

    project = UnicodeAttribute(attr_name=GENERAL_PROJECT_ID, hash_key=True)


class CustomerNameIndex(GlobalSecondaryIndex):
    class Meta(BaseMeta):
        index_name = f"{CUSTOMER_NAME}-index"
        read_capacity_units = 1
        write_capacity_units = 1
        projection = AllProjection()

    customer_name = UnicodeAttribute(hash_key=True, attr_name=CUSTOMER_NAME)


class Tenant(ModularBaseModel):
    class Meta(BaseMeta):
        table_name = f'{TABLES_PREFIX}{MODULAR_TENANTS_TABLE_NAME}'

    name = UnicodeAttribute(hash_key=True, attr_name=TENANT_NAME)
    display_name = UnicodeAttribute(attr_name=DISPLAY_NAME)
    display_name_to_lower = UnicodeAttribute(attr_name=DNTL_NAME_KEY)
    read_only = M3BooleanAttribute(attr_name=READ_ONLY, null=True)
    is_active = M3BooleanAttribute(attr_name=IS_ACTIVE, null=True)
    customer_name = UnicodeAttribute(attr_name=CUSTOMER_NAME)
    cloud = UnicodeAttribute(attr_name=CLOUD)
    activation_date = UnicodeAttribute(attr_name=ACTIVATION_DATE, null=True)
    deactivation_date = UnicodeAttribute(attr_name=DEACTIVATION_DATE,
                                         null=True)
    management_parent_id = UnicodeAttribute(attr_name=MANAGEMENT_PARENT_ID,
                                            null=True)
    project = UnicodeAttribute(attr_name=GENERAL_PROJECT_ID, null=True)
    regions = ListAttribute(of=RegionAttr, attr_name=REGIONS, default=list)
    contacts = Contacts(attr_name=TENANT_CONTACT, null=True)
    parent_map = MapAttribute(attr_name=PARENT_MAP, default=dict)

    customer_name_index = CustomerNameIndex()
    project_index = ProjectIndex()
    dntl_c_index = DisplayNameToLowerCloudIndex()

    def get_parent_id(self, type_: str) -> Optional[str]:
        assert type_ in ALLOWED_TENANT_PARENT_MAP_KEYS
        if type_ in self.parent_map:
            return self.parent_map[type_]
        return

    @property
    def accN_index(self):
        return self.project_index

    @property
    def account_number(self) -> str | None:
        return self.project

    @account_number.setter
    def account_number(self, value: str | None):
        self.project = value
