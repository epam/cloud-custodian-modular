from pynamodb.attributes import UnicodeAttribute

from modular_sdk.models.base_meta import BaseMeta
from modular_sdk.models.pynamongo.models import ModularBaseModel

from modular_sdk.models.pynamongo.attributes import DynamicAttribute


class Setting(ModularBaseModel):
    class Meta(BaseMeta):
        table_name = 'Settings'

    name = UnicodeAttribute(hash_key=True, attr_name='s')
    value = DynamicAttribute(attr_name='v')
