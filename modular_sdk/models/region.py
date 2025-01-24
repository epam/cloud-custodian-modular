from pynamodb.attributes import UnicodeAttribute, MapAttribute, ListAttribute, AttributeContainer
from pynamodb.indexes import AllProjection

from pynamodb.indexes import GlobalSecondaryIndex
from modular_sdk.models.pynamongo.models import ModularBaseModel

from modular_sdk.models.base_meta import BaseMeta, TABLES_PREFIX
from modular_sdk.models.pynamongo.attributes import M3BooleanAttribute

REGION_CLOUD = 'c'
REGION_NATIVE_NAME = 'nn'
REGION_NAME = 'r'
REGION_ID = 'rId'
REGIONS_FIELDS = 'f'
REGION_AVZ = 'avz'
ACTIVE = 'act'
HARDWARE = 'hw'
HIDDEN = 'hid'
DEPRECATED = 'dep'
UNREACHABLE = 'unr'
REGION_ABBREVIATION = 'na'
BILLING_MIX_MODE = 'bilM'
BILLING_DISABLED = "bilD"


MODULAR_REGIONS_TABLE_NAME = 'Regions'


# Region class is a model for Table 'Regions' and an Attribute in Tenant model,
# must be inherited to avoid exception with MapAttribute
class BaseRegion(AttributeContainer):
    maestro_name = UnicodeAttribute(hash_key=True, attr_name=REGION_NAME)
    native_name = UnicodeAttribute(attr_name=REGION_NATIVE_NAME)
    cloud = UnicodeAttribute(attr_name=REGION_CLOUD)
    region_id = UnicodeAttribute(attr_name=REGION_ID)
    is_active = M3BooleanAttribute(attr_name=ACTIVE, null=True)

    availability_zones = ListAttribute(attr_name=REGION_AVZ, default=list)
    fields = MapAttribute(attr_name=REGIONS_FIELDS, default=dict)
    region_abbreviation = UnicodeAttribute(attr_name=REGION_ABBREVIATION,
                                           null=True)
    billing_mix_mode = M3BooleanAttribute(attr_name=BILLING_MIX_MODE, null=True)
    billing_disabled = M3BooleanAttribute(attr_name=BILLING_DISABLED, null=True)
    is_hardware = M3BooleanAttribute(attr_name=HARDWARE, null=True)
    is_hidden = M3BooleanAttribute(attr_name=HIDDEN, null=True)
    is_deprecated = M3BooleanAttribute(attr_name=DEPRECATED, null=True)
    is_unreachable = M3BooleanAttribute(attr_name=UNREACHABLE, null=True)


class NativeNameCloudIndex(GlobalSecondaryIndex):
    class Meta(BaseMeta):
        index_name = f'{REGION_NATIVE_NAME}-{REGION_CLOUD}-index'
        read_capacity_units = 1
        write_capacity_units = 1
        projection = AllProjection()

    native_name = UnicodeAttribute(attr_name=REGION_NATIVE_NAME, hash_key=True)
    cloud = UnicodeAttribute(attr_name=REGION_CLOUD, range_key=True)


class RegionModel(ModularBaseModel, BaseRegion):
    class Meta(BaseMeta):
        table_name = f'{TABLES_PREFIX}{MODULAR_REGIONS_TABLE_NAME}'

    native_name_cloud_index = NativeNameCloudIndex()


class RegionAttr(MapAttribute, BaseRegion):
    pass
