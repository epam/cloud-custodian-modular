from pynamodb.attributes import UnicodeAttribute, \
    UTCDateTimeAttribute, NumberAttribute
from pynamodb.indexes import AllProjection

from pynamodb.indexes import GlobalSecondaryIndex
from modular_sdk.models.pynamongo.models import ModularBaseModel

from modular_sdk.models.base_meta import BaseMeta


class SegmentIndex(GlobalSecondaryIndex):
    class Meta(BaseMeta):
        index_name = 'segment-index'
        read_capacity_units = 1
        write_capacity_units = 1
        projection = AllProjection()

    segment = UnicodeAttribute(hash_key=True)
    execution_id = UnicodeAttribute(range_key=True)


class ExecutionTrace(ModularBaseModel):
    class Meta(BaseMeta):
        table_name = 'ExecutionTraces'

    component = UnicodeAttribute(hash_key=True)
    execution_id = UnicodeAttribute(range_key=True)
    segment = UnicodeAttribute()
    segment_index = SegmentIndex()

    start_time = UTCDateTimeAttribute()
    end_time = UTCDateTimeAttribute()
    duration_seconds = NumberAttribute()
