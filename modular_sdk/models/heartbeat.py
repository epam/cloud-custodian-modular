from pynamodb.attributes import UnicodeAttribute, MapAttribute, \
    UTCDateTimeAttribute

from modular_sdk.models.pynamongo.models import ModularBaseModel

from modular_sdk.models.base_meta import BaseMeta


class Heartbeat(ModularBaseModel):
    class Meta(BaseMeta):
        table_name = 'Heartbeats'

    component = UnicodeAttribute(hash_key=True)
    event_date = UTCDateTimeAttribute(range_key=True)
    health_check = MapAttribute(default=dict)
