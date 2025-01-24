from datetime import datetime, timezone

import pytest
from pynamodb.attributes import UnicodeAttribute, JSONAttribute, \
    BooleanAttribute, NumberAttribute, UTCDateTimeAttribute, TTLAttribute, \
    NullAttribute, MapAttribute, DynamicMapAttribute, ListAttribute
from pynamodb.exceptions import DoesNotExist
from pynamodb.models import Model

from modular_sdk.models.pynamongo.adapter import PynamoDBToPymongoAdapter


@pytest.fixture()
def adapter(mongo_database):
    return PynamoDBToPymongoAdapter(mongo_database)


class Nested(MapAttribute):
    one = UnicodeAttribute(attr_name='o')
    two = UnicodeAttribute(attr_name='t')


class TestModel(Model):
    class Meta:
        table_name = 'TestModel'

    unicode = UnicodeAttribute(hash_key=True)
    json = JSONAttribute()
    boolean = BooleanAttribute()
    number = NumberAttribute()
    datetime = UTCDateTimeAttribute()
    ttl = TTLAttribute()
    null = NullAttribute(null=True)
    map = MapAttribute(default=dict)
    nested = Nested(default=dict)
    dynamic_map = DynamicMapAttribute(default=dict)
    list = ListAttribute(default=list)

    short_name = UnicodeAttribute(attr_name='s', null=True)


@pytest.fixture()
def model_instance() -> TestModel:
    return TestModel(
        unicode='test',
        json={'key': 'value'},
        boolean=True,
        number=42.142322,
        datetime=datetime(2024, 12, 20, 15, 0, 0, tzinfo=timezone.utc),
        ttl=datetime(2024, 12, 20, 15, 0, 0, tzinfo=timezone.utc),
        null=True,
        map={'key': 'value', 'key2': [1, 2, 3]},
        nested={'one': 'two', 'two': 'three'},
        dynamic_map={'key': 'value'},
        list=['one', 'two'],
        short_name='short'
    )


def test_save_get(adapter, model_instance):
    adapter.save(model_instance)

    from_db = adapter.get(TestModel, hash_key='test')
    assert from_db.unicode == 'test'
    assert from_db.json == {'key': 'value'}
    assert from_db.boolean is True
    assert from_db.number == 42.142322
    assert from_db.datetime == datetime(2024, 12, 20, 15, 0, 0,
                                        tzinfo=timezone.utc)
    assert from_db.ttl == datetime(2024, 12, 20, 15, 0, 0, tzinfo=timezone.utc)
    assert from_db.null is None  # PynamoDB's behavior
    assert from_db.map.as_dict() == {'key': 'value', 'key2': [1, 2, 3]}
    assert from_db.nested.as_dict() == {'one': 'two', 'two': 'three'}
    assert from_db.dynamic_map.as_dict() == {'attribute_values': {},
                                             'key': 'value'}
    assert from_db.list == ['one', 'two']
    assert from_db.short_name == 'short'


def test_delete(adapter, model_instance):
    with pytest.raises(DoesNotExist):
        adapter.get(TestModel, hash_key='test')

    adapter.save(model_instance)
    assert model_instance.__mongo_id__, "Mongo ID should be set after save"

    item = adapter.get(TestModel, hash_key='test')
    assert item
    assert item.__mongo_id__, "Mongo ID should be set after get"

    adapter.delete(item)

    with pytest.raises(DoesNotExist):
        adapter.get(TestModel, hash_key='test')


def test_update(adapter, model_instance):
    adapter.save(model_instance)
    # NOTE: these update below produce simple mongo update query,
    # not an aggregation pipeline
    adapter.update(model_instance, actions=[
        TestModel.boolean.set(False),
        TestModel.list.set(TestModel.list.append(['three'])),
        TestModel.list[0].set('zero'),
        TestModel.short_name.remove(),
        TestModel.map['some_key'].set('some_value'),
        TestModel.datetime.set(
            datetime(2023, 12, 20, 15, 0, 0, tzinfo=timezone.utc)),
        TestModel.json.set({'new_key': 'new_value'}),
    ])
    queried = adapter.get(TestModel, hash_key='test')
    for instance in (model_instance, queried):
        assert instance.boolean is False
        assert instance.list == ['zero', 'two', 'three']
        assert instance.short_name is None
        assert instance.map.as_dict() == {'key': 'value', 'key2': [1, 2, 3],
                                          'some_key': 'some_value'}
        assert instance.datetime == datetime(2023, 12, 20, 15, 0, 0,
                                             tzinfo=timezone.utc)
        assert instance.json == {'new_key': 'new_value'}


def test_update_pipeline(adapter, model_instance):
    """
    PynamoDB updates that reference another attribute are converted to
    MongoDB aggregation pipeline stages.
    Also, it's possible to do TestModel.list[0].remove(). But it's not
    supported by mongomock
    """
    adapter.save(model_instance)
    adapter.update(model_instance, actions=[
        TestModel.number.set(TestModel.number + 1),
    ])
    assert adapter.get(TestModel, hash_key='test').number == 43.142322

    adapter.update(model_instance, actions=[
        TestModel.number.set(TestModel.number + TestModel.number),
    ])
    assert adapter.get(TestModel, hash_key='test').number == 86.284644


def test_refresh(adapter, model_instance):
    adapter.save(model_instance)

    model_instance.boolean = False
    model_instance.number = 1
    model_instance.map = {}
    model_instance.list = []

    adapter.refresh(model_instance)
    assert model_instance.boolean is True
    assert model_instance.number == 42.142322
    assert model_instance.map.as_dict() == {'key': 'value', 'key2': [1, 2, 3]}
    assert model_instance.list == ['one', 'two']
