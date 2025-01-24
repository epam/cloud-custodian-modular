from pynamodb.attributes import UnicodeAttribute, ListAttribute

from modular_sdk.models.pynamongo.models import ModularBaseModel
from modular_sdk.models.base_meta import BaseMeta, TABLES_PREFIX
from modular_sdk.models.pynamongo.attributes import M3BooleanAttribute

NAME_KEY = 'n'
DISPLAY_NAME_KEY = 'dn'
CUSTOMER_ADMINS = 'ca'
ACTIVE = 'act'

MODULAR_CUSTOMERS_TABLE_NAME = 'Customers'


class Customer(ModularBaseModel):
    class Meta(BaseMeta):
        table_name = f'{TABLES_PREFIX}{MODULAR_CUSTOMERS_TABLE_NAME}'

    name = UnicodeAttribute(hash_key=True, attr_name=NAME_KEY)
    display_name = UnicodeAttribute(attr_name=DISPLAY_NAME_KEY, null=True)
    admins = ListAttribute(attr_name=CUSTOMER_ADMINS, default=list)
    is_active = M3BooleanAttribute(attr_name=ACTIVE, null=True)
