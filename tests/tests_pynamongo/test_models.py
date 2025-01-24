import pytest
from unittest.mock import MagicMock
from modular_sdk.models.pynamongo.models import SafeUpdateModel
from pynamodb.attributes import MapAttribute, UnicodeAttribute, ListAttribute, NumberAttribute, BooleanAttribute

from pynamodb.constants import ITEM
KEY_NAME = 'k'
STR_NAME = 's'
NUMBER_NAME = 'n'
BOOL_NAME = 'b'
LIST_STR_NAME = 'ls'
LIST_MAP_NAME = 'lm'
LIST_MAP_CUSTOM_NAME = 'lmc'
MAP_NAME = 'm'
MAP_CUSTOM_NAME = 'mc'


class ExampleMapAttrPartial(MapAttribute):
    string = UnicodeAttribute(attr_name=STR_NAME)
    list_string = ListAttribute(
        of=UnicodeAttribute, null=True, attr_name=LIST_STR_NAME
    )


class ExampleMapAttrFull(MapAttribute):
    string = UnicodeAttribute(attr_name=STR_NAME)
    number = NumberAttribute(attr_name=NUMBER_NAME)
    boolean = BooleanAttribute(attr_name=BOOL_NAME)
    list_string = ListAttribute(
        of=UnicodeAttribute, null=True, attr_name=LIST_STR_NAME
    )
    mapping = MapAttribute(null=True, attr_name=MAP_NAME)


class TestModel1(SafeUpdateModel):
    class Meta:
        table_name = 'User'
        region = 'us-west-1'

    key = UnicodeAttribute(hash_key=True, attr_name=KEY_NAME)


class TestModel2(SafeUpdateModel):
    class Meta:
        table_name = 'User'
        region = 'us-west-1'

    key = UnicodeAttribute(hash_key=True, attr_name=KEY_NAME)
    string = UnicodeAttribute(attr_name=STR_NAME)
    number = NumberAttribute(attr_name=NUMBER_NAME)
    boolean = BooleanAttribute(attr_name=BOOL_NAME)
    mapping = MapAttribute(default=dict, attr_name=MAP_NAME)
    list_string = ListAttribute(
        of=UnicodeAttribute, default=list, attr_name=LIST_STR_NAME
    )
    list_mapping = ListAttribute(
        of=MapAttribute, default=list, attr_name=LIST_MAP_NAME
    )


class TestModel3PartialMapCustom(SafeUpdateModel):
    class Meta:
        table_name = 'User'
        region = 'us-west-1'

    key = UnicodeAttribute(hash_key=True, attr_name=KEY_NAME)
    string = UnicodeAttribute(attr_name=STR_NAME)
    number = NumberAttribute(attr_name=NUMBER_NAME)
    boolean = BooleanAttribute(attr_name=BOOL_NAME)
    mapping = MapAttribute(default=dict, attr_name=MAP_NAME)
    list_string = ListAttribute(
        of=UnicodeAttribute, default=list, attr_name=LIST_STR_NAME
    )
    list_mapping = ListAttribute(
        of=MapAttribute, default=list, attr_name=LIST_MAP_NAME
    )

    mapping_custom = ExampleMapAttrPartial(default=dict, attr_name=MAP_CUSTOM_NAME)
    list_mapping_custom = ListAttribute(
        of=ExampleMapAttrFull, default=list, attr_name=LIST_MAP_CUSTOM_NAME
    )


class TestModel4PartialListMapCustom(SafeUpdateModel):
    class Meta:
        table_name = 'User'
        region = 'us-west-1'

    key = UnicodeAttribute(hash_key=True, attr_name=KEY_NAME)
    string = UnicodeAttribute(attr_name=STR_NAME)
    number = NumberAttribute(attr_name=NUMBER_NAME)
    boolean = BooleanAttribute(attr_name=BOOL_NAME)
    mapping = MapAttribute(default=dict, attr_name=MAP_NAME)
    list_string = ListAttribute(
        of=UnicodeAttribute, default=list, attr_name=LIST_STR_NAME
    )
    list_mapping = ListAttribute(
        of=MapAttribute, default=list, attr_name=LIST_MAP_NAME
    )

    mapping_custom = ExampleMapAttrFull(default=dict, attr_name=MAP_CUSTOM_NAME)
    list_mapping_custom = ListAttribute(
        of=ExampleMapAttrPartial, default=list, attr_name=LIST_MAP_CUSTOM_NAME
    )


@pytest.fixture
def raw_data() -> dict:
    return {
        KEY_NAME: {'S': 'value'},
        STR_NAME: {'S': 'str'},
        NUMBER_NAME: {'N': '1'},
        BOOL_NAME: {'BOOL': True},
        LIST_STR_NAME: {'L': [{'S': 'one'}, {'S': 'two'}, {'S': 'three'}]},
        LIST_MAP_NAME: {
            'L': [{'M': {'key': {'S': 'value'}, 'key1': {'S': 'value1'}}}]
        },
        LIST_MAP_CUSTOM_NAME: {
            'L': [
                {
                    'M': {
                        STR_NAME: {'S': 'str'},
                        NUMBER_NAME: {'N': '1'},
                        BOOL_NAME: {'BOOL': True},
                        LIST_STR_NAME: {
                            'L': [
                                {'S': 'one'},
                                {'S': 'two'},
                                {'S': 'three'},
                            ]
                        },
                        MAP_NAME: {'M': {'key': {'S': 'value'}}},
                    }
                },
                {
                    'M': {
                        STR_NAME: {'S': 'str'},
                        NUMBER_NAME: {'N': '2'},
                        BOOL_NAME: {'BOOL': False},
                    }
                },
            ]
        },
        MAP_NAME: {'M': {'key': {'S': 'value'}}},
        MAP_CUSTOM_NAME: {
            'M': {
                STR_NAME: {'S': 'str'},
                NUMBER_NAME: {'N': '1'},
                BOOL_NAME: {'BOOL': True},
                LIST_STR_NAME: {
                    'L': [{'S': 'one'}, {'S': 'two'}, {'S': 'three'}]
                },
                MAP_NAME: {'M': {'key': {'S': 'value'}}},
            }
        },
    }


class TestSafeUpdateModel:
    @staticmethod
    def patch_get_item(model: type[SafeUpdateModel], item: dict) -> type[SafeUpdateModel]:
        """
        Patches model cls._get_connection().get_item() so that it return
        the given item.
        :param model:
        :param item:
        :return:
        """

        class Mocked(model):
            pass

        Mocked._get_connection = MagicMock()
        Mocked._get_connection().get_item.return_value = {ITEM: item}
        return Mocked

    def test_commons(self, raw_data):
        model = self.patch_get_item(TestModel1, raw_data)
        item = model.get_nullable('mock')

        _should_not_exist = (
            STR_NAME,
            NUMBER_NAME,
            BOOL_NAME,
            LIST_STR_NAME,
            LIST_MAP_NAME,
            LIST_MAP_CUSTOM_NAME,
            MAP_NAME,
        )
        for attr in _should_not_exist:
            assert not hasattr(item, attr)

        assert hasattr(item, model._original_data_attr_name)
        original_data = getattr(item, model._original_data_attr_name)
        assert isinstance(original_data, dict)
        item.save()
        model._get_connection().put_item.assert_called()

    def test_model1(self, raw_data):
        model = self.patch_get_item(TestModel1, raw_data)
        item = model.get_nullable('mock')

        assert item.key == 'value'

        original_data = getattr(item, model._original_data_attr_name)
        assert original_data == raw_data

        item.save()
        keys = model._get_connection().put_item.call_args.args
        saved_data = model._get_connection().put_item.call_args.kwargs[
            'attributes'
        ]
        assert keys == (item.key, )
        raw_data.pop(KEY_NAME)
        assert raw_data == saved_data

    def test_model2(self, raw_data):
        model = self.patch_get_item(TestModel2, raw_data)
        item = model.get_nullable('mock')

        assert item.key == 'value'
        assert item.string == 'str'
        assert item.number == 1
        assert item.boolean is True
        assert item.mapping.as_dict() == {'key': 'value'}
        assert item.list_string == ['one', 'two', 'three']
        assert item.list_mapping == [{'key': 'value', 'key1': 'value1'}]

        item.save()
        keys = model._get_connection().put_item.call_args.args
        saved_data = model._get_connection().put_item.call_args.kwargs[
            'attributes'
        ]
        assert keys == (item.key, )
        raw_data.pop(KEY_NAME)
        assert raw_data == saved_data

    def test_model3(self, raw_data):
        model = self.patch_get_item(TestModel3PartialMapCustom, raw_data)
        item = model.get_nullable('mock')
        assert item.mapping_custom.as_dict() == {'string': 'str', 'list_string': ['one', 'two', 'three']}

        item.save()
        keys = model._get_connection().put_item.call_args.args
        saved_data = model._get_connection().put_item.call_args.kwargs[
            'attributes'
        ]
        assert keys == (item.key, )
        raw_data.pop(KEY_NAME)
        assert raw_data == saved_data

    def test_model4(self, raw_data):
        model = self.patch_get_item(TestModel4PartialListMapCustom, raw_data)
        item = model.get_nullable('mock')
        assert item.list_mapping_custom[0].as_dict() == {'list_string': ['one', 'two', 'three'], 'string': 'str'}
        assert item.list_mapping_custom[1].as_dict() == {'string': 'str'}

        item.save()
        keys = model._get_connection().put_item.call_args.args
        saved_data = model._get_connection().put_item.call_args.kwargs[
            'attributes'
        ]
        assert keys == (item.key, )
        raw_data.pop(KEY_NAME)
        assert raw_data == saved_data
