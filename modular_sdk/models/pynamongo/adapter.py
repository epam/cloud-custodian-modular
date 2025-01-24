import json
import base64
import binascii
from typing import TYPE_CHECKING, Generator, Iterator, TypeVar

from pymongo import ASCENDING, DESCENDING, DeleteOne, ReplaceOne
from pymongo.collection import ReturnDocument
from pynamodb.models import Model

from modular_sdk.commons.log_helper import get_logger
from modular_sdk.models.pynamongo.convertors import (
    PynamoDBModelToMongoDictSerializer,
    convert_attributes_to_get,
    convert_condition_expression,
    convert_update_expression,
    merge_update_expressions
)

if TYPE_CHECKING:
    from pymongo.collection import Collection
    from pymongo.cursor import Cursor
    from pynamodb.expressions.update import Action

_MT = TypeVar('_MT', bound=Model)

_LOG = get_logger(__name__)


class ResultIterator(Iterator[_MT]):
    __slots__ = '_cursor', '_model', '_serializer', '_skip'

    def __init__(
        self,
        cursor: 'Cursor',
        model: type[_MT],
        serializer: PynamoDBModelToMongoDictSerializer,
        skip: int = 0,
    ):
        self._cursor = cursor
        self._model = model
        self._serializer = serializer
        self._skip = skip

    def __iter__(self) -> 'ResultIterator':
        return self

    def __next__(self) -> _MT:
        item = self._cursor.__next__()
        self._skip += 1
        return self._serializer.deserialize(self._model, item)

    def next(self) -> _MT:
        return self.__next__()

    @property
    def last_evaluated_key(self):
        return self._skip

    @property
    def total_count(self) -> int:
        return self._cursor.retrieved


class EmptyResultIterator(ResultIterator):
    __slots__ = '_lek'

    def __init__(self, last_evaluated_key=None):
        self._lek = last_evaluated_key

    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration('Cannot iterate over empty result iterator')

    @property
    def last_evaluated_key(self):
        return self._lek

    @property
    def total_count(self):
        return 0


class BatchWrite:
    __slots__ = '_ser', '_collection', '_req'

    def __init__(
        self,
        serializer: PynamoDBModelToMongoDictSerializer,
        collection: 'Collection',
    ):
        self._ser = serializer
        self._collection = collection
        self._req = []

    def save(self, put_item: Model) -> None:
        if _id := self._ser.get_mongo_id(put_item):
            q = {'_id': _id}
        else:
            q = self._ser.instance_serialized_keys(put_item)
        self._req.append(
            ReplaceOne(
                filter=q,
                replacement=self._ser.serialize(put_item),
                upsert=True,
            )
        )

    def delete(self, del_item: Model) -> None:
        if _id := self._ser.get_mongo_id(del_item):
            q = {'_id': _id}
        else:
            q = self._ser.instance_serialized_keys(del_item)
        self._req.append(DeleteOne(q))

    def __enter__(self):
        self._req.clear()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return self.commit()

    def commit(self) -> None:
        if not self._req:
            return
        self._collection.bulk_write(self._req)


class PynamoDBToPymongoAdapter:
    __slots__ = ('_db',)
    _ser = PynamoDBModelToMongoDictSerializer()

    def __init__(self, db: 'Database | None' = None):
        self._db = db

    @property
    def mongo_database(self) -> 'Database | None':
        return self._db

    def get_collection(self, model: type[Model] | Model) -> 'Collection':
        collection = getattr(model.Meta, 'mongo_collection', None)
        if collection is not None:
            return collection

        db = getattr(model.Meta, 'mongo_database', self._db)
        assert db is not None, (
            'Mongo database must be set either to model`s '
            'Meta or to PynamoDBToPymongoAdapter'
        )
        col = db.get_collection(model.Meta.table_name)
        setattr(model.Meta, 'mongo_collection', col)
        return col

    def get(
        self,
        model: type[_MT],
        hash_key,
        range_key=None,
        attributes_to_get=None,
    ) -> _MT:
        hash_key_name, range_key_name = self._ser.model_keys_names(model)
        hash_key, range_key = self._ser.serialize_keys(
            model, hash_key, range_key
        )
        query = {hash_key_name: hash_key}
        if range_key_name and range_key:
            query[range_key_name] = range_key

        item = self.get_collection(model).find_one(
            query, projection=convert_attributes_to_get(attributes_to_get)
        )
        if not item:
            raise model.DoesNotExist()
        return self._ser.deserialize(model, item)

    def save(self, instance: Model) -> dict:
        collection = self.get_collection(instance)
        if _id := self._ser.get_mongo_id(instance):
            q = {'_id': _id}
        else:
            q = self._ser.instance_serialized_keys(instance)
        res = collection.replace_one(
            filter=q, replacement=self._ser.serialize(instance), upsert=True
        )
        if _id := res.upserted_id:
            self._ser.set_mongo_id(instance, _id)
        return {
            'ConsumedCapacity': {
                'CapacityUnits': 1.0,
                'TableName': instance.Meta.table_name,
            }
        }

    def update(self, instance: Model, actions: list['Action']) -> dict:
        _update = merge_update_expressions(
            map(convert_update_expression, actions)
        )
        if _id := self._ser.get_mongo_id(instance):
            q = {'_id': _id}
        else:
            q = self._ser.instance_serialized_keys(instance)
        res = self.get_collection(instance).find_one_and_update(
            filter=q,
            update=_update,
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if res:
            self._ser.deserialize_to(instance, res)
        return {
            'ConsumedCapacity': {
                'CapacityUnits': 1.0,
                'TableName': instance.Meta.table_name,
            }
        }

    def delete(self, instance: Model) -> dict:
        if _id := self._ser.get_mongo_id(instance):
            q = {'_id': _id}
        else:
            q = self._ser.instance_serialized_keys(instance)

        self.get_collection(instance).delete_one(q)
        return {
            'ConsumedCapacity': {
                'CapacityUnits': 1.0,
                'TableName': instance.Meta.table_name,
            }
        }

    def refresh(self, instance: Model) -> None:
        if _id := self._ser.get_mongo_id(instance):
            q = {'_id': _id}
        else:
            q = self._ser.instance_serialized_keys(instance)
        item = self.get_collection(instance).find_one(q)
        if not item:
            raise instance.DoesNotExist()
        self._ser.deserialize_to(instance, item)

    def exists(self, model: type[Model]) -> bool:
        db = self.get_collection(model).database
        return model.Meta.table_name in db.list_collection_names()

    def delete_table(self, model: type[Model]) -> None:
        self.get_collection(model).drop()

    def create_table(self, model: type[Model]) -> None:
        """
        Mongo table is created automatically
        """
        # db = self._get_db(model)
        # db.create_collection()

    def count(
        self,
        model: type[Model],
        hash_key=None,
        range_key_condition=None,
        filter_condition=None,
        index_name=None,
        limit=None,
    ) -> int:
        query = {}

        if hash_key:
            if index_name:
                index = self._ser.model_indexes(model).get(index_name)
                assert index is not None, 'Index must exist'

                h_attr, _ = self._ser.index_keys(index)
                query[h_attr.attr_name] = h_attr.serialize(hash_key)
            else:
                hash_key_name, _ = self._ser.model_keys_names(model)
                hash_key, _ = self._ser.serialize_keys(model, hash_key, None)
                query[hash_key_name] = hash_key

        if range_key_condition is not None:
            query.update(convert_condition_expression(range_key_condition))
        if filter_condition is not None:
            query.update(convert_condition_expression(filter_condition))
        collection = self.get_collection(model)

        if limit:
            return collection.count_documents(query, limit=limit)
        return collection.count_documents(query)

    def query(
        self,
        model: type[_MT],
        hash_key,
        range_key_condition=None,
        filter_condition=None,
        index_name: str | None = None,
        scan_index_forward=True,
        limit=None,
        last_evaluated_key=None,
        attributes_to_get=None,
        page_size=None,
    ) -> ResultIterator[_MT]:
        if index_name:
            index = self._ser.model_indexes(model).get(index_name)
            assert index is not None, 'Index must exist'
            h_attr, r_attr = self._ser.index_keys(index)
            hash_key_name = h_attr.attr_name
            range_key_name = r_attr.attr_name if r_attr is not None else None
            hash_key = h_attr.serialize(hash_key)
        else:
            hash_key_name, range_key_name = self._ser.model_keys_names(model)
            hash_key, _ = self._ser.serialize_keys(model, hash_key, None)

        q = {hash_key_name: hash_key}
        if range_key_condition is not None:
            q.update(convert_condition_expression(range_key_condition))
        if filter_condition is not None:
            q.update(convert_condition_expression(filter_condition))
        last_evaluated_key = last_evaluated_key or 0

        cursor = self.get_collection(model).find(
            q,
            projection=convert_attributes_to_get(attributes_to_get),
            skip=last_evaluated_key,
            limit=limit or 0,
            batch_size=page_size or 0,
        )
        if range_key_name:
            cursor = cursor.sort(
                range_key_name, ASCENDING if scan_index_forward else DESCENDING
            )
        return ResultIterator(
            cursor=cursor,
            model=model,
            serializer=self._ser,
            skip=last_evaluated_key,
        )

    def scan(
        self,
        model: type[_MT],
        filter_condition=None,
        limit=None,
        last_evaluated_key=None,
        page_size=None,
        index_name: str | None = None,
        attributes_to_get=None,
    ) -> ResultIterator[_MT]:
        query = {}
        if filter_condition is not None:
            query.update(convert_condition_expression(filter_condition))
        last_evaluated_key = last_evaluated_key or 0

        # TODO: scan a specific index
        cursor = self.get_collection(model).find(
            query,
            projection=convert_attributes_to_get(attributes_to_get),
            skip=last_evaluated_key,
            limit=limit or 0,
            batch_size=page_size or 0,
        )
        return ResultIterator(
            cursor=cursor,
            model=model,
            serializer=self._ser,
            skip=last_evaluated_key,
        )

    def batch_get(
        self, model: type[_MT], items: list[tuple], attributes_to_get=None
    ) -> Generator[_MT, None, None]:
        """
        Seems like bulk read is not supported.
        Order not guaranteed
        """
        ors = []

        hash_key_name, range_key_name = self._ser.model_keys_names(model)
        for key in items:
            hash_key, range_key = self._ser.serialize_keys(model, *key)
            q = {hash_key_name: hash_key}
            if range_key_name and range_key:
                q[range_key_name] = range_key
            ors.append(q)
        cursor = self.get_collection(model).find(
            {'$or': ors},
            projection=convert_attributes_to_get(attributes_to_get),
        )
        for item in cursor:
            yield self._ser.deserialize(model, item)

    def batch_write(self, model: type[Model]) -> BatchWrite:
        return BatchWrite(
            serializer=self._ser, collection=self.get_collection(model)
        )


class LastEvaluatedKey:
    """
    Simple abstraction over DynamoDB last evaluated key & MongoDB offset :)
    """
    payload_key_name = 'key'

    def __init__(self, lek: dict | int | None = None):
        self._lek = lek

    def serialize(self) -> str:
        payload = {self.payload_key_name: self._lek}
        return base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        ).decode()

    @classmethod
    def deserialize(cls, s: str | None = None) -> 'LastEvaluatedKey':
        if not s or not isinstance(s, str):
            return cls()
        _payload = {}
        try:
            decoded = base64.urlsafe_b64decode(s.encode()).decode()
            _payload = json.loads(decoded)
        except binascii.Error:
            _LOG.warning('Invalid base64 encoding in last evaluated key token')
        except json.JSONDecodeError:
            _LOG.warning('Invalid json string within last evaluated key token')
        except Exception as e:  # you never know :)
            _LOG.warning('Some unexpected exception occurred while '
                         f'deserializing last evaluated key token : \'{e}\'')
        return cls(_payload.get(cls.payload_key_name))

    @property
    def value(self) -> dict | int | None:
        return self._lek

    @value.setter
    def value(self, v: dict | int | None):
        self._lek = v

    def __bool__(self) -> bool:
        return bool(self._lek)
