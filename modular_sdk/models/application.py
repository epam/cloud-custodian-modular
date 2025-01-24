from pynamodb.attributes import UnicodeAttribute, BooleanAttribute, \
    MapAttribute, NumberAttribute
from pynamodb.indexes import AllProjection

from modular_sdk.models.base_meta import BaseMeta, TABLES_PREFIX
from pynamodb.indexes import GlobalSecondaryIndex
from modular_sdk.models.pynamongo.models import ModularBaseModel

APPLICATION_ID = 'aid'
CUSTOMER_ID = 'cid'
TYPE = 't'
DESCRIPTION = 'descr'
IS_DELETED = 'd'
DELETION_DATE = 'dd' # todo deprecated
META = 'meta'
SECRET = 'sec'
CREATION_TIMESTAMP = 'ct'
UPDATE_TIMESTAMP = 'ut'
DELETION_TIMESTAMP = 'dt'
UPDATED_BY = 'ub'
CREATED_BY = 'cb'

MODULAR_APPLICATIONS_TABLE_NAME = 'Applications'


class CustomerIdTypeIndex(GlobalSecondaryIndex):
    class Meta(BaseMeta):
        index_name = f"{CUSTOMER_ID}-{TYPE}-index"
        read_capacity_units = 1
        write_capacity_units = 1
        projection = AllProjection()

    customer_id = UnicodeAttribute(hash_key=True, attr_name=CUSTOMER_ID)
    type = UnicodeAttribute(range_key=True, attr_name=TYPE)


class Application(ModularBaseModel):
    class Meta(BaseMeta):
        table_name = f'{TABLES_PREFIX}{MODULAR_APPLICATIONS_TABLE_NAME}'

    application_id = UnicodeAttribute(hash_key=True, attr_name=APPLICATION_ID)
    customer_id = UnicodeAttribute(attr_name=CUSTOMER_ID)
    type = UnicodeAttribute(attr_name=TYPE)
    description = UnicodeAttribute(attr_name=DESCRIPTION)
    is_deleted = BooleanAttribute(attr_name=IS_DELETED)
    deletion_date = UnicodeAttribute(attr_name=DELETION_DATE, null=True) # todo deprecated
    meta = MapAttribute(default=dict, attr_name=META)
    secret = UnicodeAttribute(null=True, attr_name=SECRET)
    creation_timestamp = NumberAttribute(attr_name=CREATION_TIMESTAMP, null=True)
    update_timestamp = NumberAttribute(attr_name=UPDATE_TIMESTAMP, null=True)
    deletion_timestamp = NumberAttribute(attr_name=DELETION_TIMESTAMP, null=True)
    updated_by = UnicodeAttribute(attr_name=UPDATED_BY, null=True)
    created_by = UnicodeAttribute(attr_name=CREATED_BY, null=True)

    customer_id_type_index = CustomerIdTypeIndex()
