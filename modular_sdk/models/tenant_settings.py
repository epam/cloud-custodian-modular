from pynamodb.attributes import UnicodeAttribute, MapAttribute

from pynamodb.indexes import GlobalSecondaryIndex
from modular_sdk.models.pynamongo.models import ModularBaseModel

from modular_sdk.models.base_meta import BaseMeta, TABLES_PREFIX
from pynamodb.indexes import AllProjection


TENANT_NAME = 't'
KEY = 'k'
VALUE = 'v'

MODULAR_TENANT_SETTINGS_TABLE_NAME = 'TenantSettings'


class KeyTenantNameIndex(GlobalSecondaryIndex):
    class Meta(BaseMeta):
        index_name = f'{KEY}-index'
        read_capacity_units = 1
        write_capacity_units = 1
        projection = AllProjection()

    key = UnicodeAttribute(hash_key=True, attr_name=KEY)


class TenantSettings(ModularBaseModel):
    class Meta(BaseMeta):
        table_name = f'{TABLES_PREFIX}{MODULAR_TENANT_SETTINGS_TABLE_NAME}'

    tenant_name = UnicodeAttribute(hash_key=True, attr_name=TENANT_NAME)
    key = UnicodeAttribute(range_key=True, attr_name=KEY)

    value = MapAttribute(attr_name=VALUE, default=dict)
    key_tenant_name_index = KeyTenantNameIndex()
