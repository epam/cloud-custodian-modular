from typing import Optional

from pynamodb.attributes import UnicodeAttribute, MapAttribute, \
    BooleanAttribute, NumberAttribute
from pynamodb.indexes import AllProjection

from pynamodb.indexes import GlobalSecondaryIndex
from modular_sdk.models.pynamongo.models import ModularBaseModel

from modular_sdk.commons.constants import COMPOUND_KEYS_SEPARATOR, ParentScope
from modular_sdk.models.base_meta import BaseMeta, TABLES_PREFIX

PARENT_ID = 'pid'
CUSTOMER_ID = 'cid'
APPLICATION_ID = 'aid'
TYPE = 't'
DESCRIPTION = 'descr'
META = 'meta'
IS_DELETED = 'd'
DELETION_DATE = 'dd' # todo deprecated
CREATION_TIMESTAMP = 'ct'
UPDATE_TIMESTAMP = 'ut'
DELETION_TIMESTAMP = 'dt'
SCOPE_ATTR = 's'
UPDATED_BY = 'ub'
CREATED_BY = 'cb'

MODULAR_PARENTS_TABLE_NAME = 'Parents'


class CustomerIdScopeIndex(GlobalSecondaryIndex):
    class Meta(BaseMeta):
        index_name = f'{CUSTOMER_ID}-{SCOPE_ATTR}-index'
        read_capacity_units = 1
        write_capacity_units = 1
        projection = AllProjection()

    customer_id = UnicodeAttribute(hash_key=True, attr_name=CUSTOMER_ID)
    type_scope = UnicodeAttribute(range_key=True, attr_name=SCOPE_ATTR)


# this index currently does not exist. It's for the future :)
class ApplicationIdIndex(GlobalSecondaryIndex):
    class Meta(BaseMeta):
        index_name = f'{APPLICATION_ID}-index'
        read_capacity_units = 1
        write_capacity_units = 1
        projection = AllProjection()

    application_id = UnicodeAttribute(hash_key=True, attr_name=APPLICATION_ID)


class Parent(ModularBaseModel):
    class Meta(BaseMeta):
        table_name = f'{TABLES_PREFIX}{MODULAR_PARENTS_TABLE_NAME}'

    parent_id = UnicodeAttribute(hash_key=True, attr_name=PARENT_ID)
    customer_id = UnicodeAttribute(attr_name=CUSTOMER_ID)
    application_id = UnicodeAttribute(attr_name=APPLICATION_ID)
    type = UnicodeAttribute(attr_name=TYPE)
    description = UnicodeAttribute(attr_name=DESCRIPTION, null=True)
    meta = MapAttribute(attr_name=META, default=dict)
    is_deleted = BooleanAttribute(attr_name=IS_DELETED)
    deletion_date = UnicodeAttribute(attr_name=DELETION_DATE, null=True) # todo deprecated
    creation_timestamp = NumberAttribute(attr_name=CREATION_TIMESTAMP,
                                         null=True)
    update_timestamp = NumberAttribute(attr_name=UPDATE_TIMESTAMP, null=True)
    deletion_timestamp = NumberAttribute(attr_name=DELETION_TIMESTAMP,
                                         null=True)

    # in case the attribute is not null its format must
    # adhere to [type]#[scope]#[tenant|cloud]
    type_scope = UnicodeAttribute(attr_name=SCOPE_ATTR, null=True)
    updated_by = UnicodeAttribute(attr_name=UPDATED_BY, null=True)
    created_by = UnicodeAttribute(attr_name=CREATED_BY, null=True)

    customer_id_scope_index = CustomerIdScopeIndex()
    application_id_index = ApplicationIdIndex()
    # todo use if self.type is removed
    # @property
    # def type(self) -> str:
    #     return self.type_scope.split(COMPOUND_KEYS_SEPARATOR)[0]

    @property
    def scope(self) -> Optional[str]:
        if not self.type_scope:
            return
        return self.type_scope.split(COMPOUND_KEYS_SEPARATOR)[1]

    @property
    def tenant_name(self) -> Optional[str]:
        if not self.type_scope:
            return
        if self.scope == ParentScope.ALL:
            # we cannot specify tenant when scope is ALL
            return
        return self.type_scope.split(COMPOUND_KEYS_SEPARATOR)[2]

    @property
    def cloud(self) -> Optional[str]:
        if not self.type_scope:
            return
        if self.scope == ParentScope.ALL:
            # we can specify cloud only if scope ALL
            return self.type_scope.split(COMPOUND_KEYS_SEPARATOR)[2].upper()
