import pytest
from modular_sdk.models.pynamongo.convertors import (
    convert_attributes_to_get,
    convert_condition_expression,
    convert_update_expression
)
from pynamodb.attributes import (
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    UnicodeAttribute,
)
from pynamodb.models import Model


class Nested(MapAttribute):
    one = UnicodeAttribute(attr_name='o')
    two = UnicodeAttribute(attr_name='t')


class TestModel(Model):
    string = UnicodeAttribute()
    short_string = UnicodeAttribute(attr_name='s')
    number = NumberAttribute(attr_name='num')
    map = MapAttribute()
    list = ListAttribute()
    nested = Nested(attr_name='n')


def test_convert_attributes_to_get():
    assert convert_attributes_to_get() == ()
    assert convert_attributes_to_get([TestModel.string]) == ('string',)
    assert set(
        convert_attributes_to_get(
            [TestModel.short_string, TestModel.map['key']]
        )
    ) == {'s', 'map.key'}
    assert set(
        convert_attributes_to_get([TestModel.list[0], TestModel.nested.one])
    ) == {'list[0]', 'n.o'}
    assert set(
        convert_attributes_to_get(
            [TestModel.list[0], TestModel.nested.one, TestModel.nested.two]
        )
    ) == {'list[0]', 'n.o', 'n.t'}
    assert set(
        convert_attributes_to_get(
            ('string', 's', 'map', TestModel.short_string)
        )
    ) == {'string', 's', 'map', 's'}


class TestConditionExpressionConvertor:
    def test_attr_exists(self):
        assert convert_condition_expression(TestModel.list.exists()) == {
            'list': {'$exists': True}
        }

    def test_attr_does_not_exists(self):
        assert convert_condition_expression(
            TestModel.list.does_not_exist()
        ) == {'list': {'$exists': False}}

    def test_contains(self):
        assert convert_condition_expression(
            TestModel.short_string.contains('test')
        ) == {'s': {'$regex': 'test'}}

    def test_is_in(self):
        assert convert_condition_expression(
            TestModel.map['key'].is_in('one', 'two')
        ) == {'map.key': {'$in': ['one', 'two']}}

    def test_equal(self):
        assert convert_condition_expression(
            TestModel.short_string == 'test'
        ) == {'s': 'test'}

    def test_gt(self):
        assert convert_condition_expression(TestModel.number > 10) == {
            'num': {'$gt': 10}
        }

    def test_lt(self):
        assert convert_condition_expression(TestModel.number < 10) == {
            'num': {'$lt': 10}
        }

    def test_gte(self):
        assert convert_condition_expression(TestModel.number >= 10) == {
            'num': {'$gte': 10}
        }

    def test_lte(self):
        assert convert_condition_expression(TestModel.number <= 10) == {
            'num': {'$lte': 10}
        }

    def test_not_equal(self):
        assert convert_condition_expression(
            TestModel.short_string != 'test'
        ) == {'s': {'$ne': 'test'}}

    def test_between(self):
        assert convert_condition_expression(
            TestModel.number.between(10, 20)
        ) == {'num': {'$gte': 10, '$lte': 20}}

    def test_begins_with(self):
        assert convert_condition_expression(
            TestModel.short_string.startswith('test')
        ) == {'s': {'$regex': '^test'}}

    def test_and(self):
        assert convert_condition_expression(
            (TestModel.number > 10) & (TestModel.short_string == 'test')
        ) == {'$and': [{'num': {'$gt': 10}}, {'s': 'test'}]}

    def test_or(self):
        assert convert_condition_expression(
            (TestModel.number > 10) | (TestModel.short_string == 'test')
        ) == {'$or': [{'num': {'$gt': 10}}, {'s': 'test'}]}

    def test_not(self):
        assert convert_condition_expression(~(TestModel.number > 10)) == {
            '$nor': [{'num': {'$gt': 10}}]
        }

    def test_complex_condition(self):
        cond = (
            (TestModel.map['one'] == 'one') & (TestModel.map['two'] == 'two')
            | (
                (TestModel.map['three'] == 'three')
                & (~TestModel.short_string.contains('sss'))
            )
            | (TestModel.nested.one.startswith('one'))
        )
        assert convert_condition_expression(cond) == {
            '$or': [
                {
                    '$or': [
                        {'$and': [{'map.one': 'one'}, {'map.two': 'two'}]},
                        {
                            '$and': [
                                {'map.three': 'three'},
                                {'$nor': [{'s': {'$regex': 'sss'}}]},
                            ]
                        },
                    ]
                },
                {'n.o': {'$regex': '^one'}},
            ]
        }


class TestUpdateExpressionConvertor:
    def test_set(self):
        assert convert_update_expression(TestModel.short_string.set('one')) == {'$set': {'s': 'one'}}

    def test_set_list_item(self):
        assert convert_update_expression(TestModel.list[0].set(1)) == {'$set': {'list.0': 1}}

    def test_remove(self):
        assert convert_update_expression(TestModel.map["test"].remove()) == {'$unset': {'map.test': ''}}

    def test_remove_list_item(self):
        """
        With shifting
        """
        assert convert_update_expression(TestModel.list[10].remove()) == [{'$set': {'list': {'$concatArrays': [{'$slice': ['$list', 10]}, {'$slice': ['$list', {'$add': [1, 10]}, {'$size': '$list'}]}]}}}]

    def test_add_number(self):
        assert convert_update_expression(TestModel.number.add(10)) == {'$inc': {'num': 10}}

    def test_append(self):
        assert convert_update_expression(TestModel.list.set(TestModel.list.append([1,2,3]))) == {'$push': {'list': {'$each': [1, 2, 3]}}}

    def test_prepend(self):
        assert convert_update_expression(TestModel.list.set(TestModel.list.prepend([1,2,3]))) == {'$push': {'list': {'$each': [1, 2, 3], '$position': 0}}}

    def test_add_different_attr(self):
        assert convert_update_expression(TestModel.number.set(TestModel.map['number'] + 1)) == [{'$set': {'num': {'$add': ['$map.number', 1]}}}]

    @pytest.mark.skip(reason="Currently not implemented")
    def test_add_to_set(self):
        ...

    @pytest.mark.skip(reason="Currently not implemented")
    def test_delete_from_set(self):
        ...

    @pytest.mark.skip(reason='Currently not implemented')
    def test_is_not_exists(self):
        ...


