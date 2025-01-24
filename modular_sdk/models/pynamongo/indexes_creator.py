import json
from typing import TYPE_CHECKING, Generator, cast

from pymongo import ASCENDING, DESCENDING
from pymongo.operations import IndexModel

from modular_sdk.commons.log_helper import get_logger
from modular_sdk.models.pynamongo.models import PynamoDBToPymongoAdapter

if TYPE_CHECKING:
    from pynamodb.models import Model

_LOG = get_logger(__name__)


class IndexesCreator:
    """
    Creates MongoDB indexes that correspond to declared PynamoDB indexes
    """

    __slots__ = '_adapter', '_main_index_name', '_ignore', '_ho', '_ro'

    def __init__(
        self,
        db: 'Database | None' = None,
        main_index_name: str = 'main',
        ignore_indexes: tuple[str, ...] = (),
        hash_key_order=ASCENDING,
        range_key_order=DESCENDING,
    ):
        self._adapter = PynamoDBToPymongoAdapter(db)
        self._main_index_name = main_index_name
        self._ignore = ignore_indexes
        self._ho = hash_key_order
        self._ro = range_key_order

    @staticmethod
    def _get_hash_range_names(model: type['Model']) -> tuple[str, str | None]:
        h, r = None, None
        for attr in model.get_attributes().values():
            if attr.is_hash_key:
                h = attr.attr_name
            if attr.is_range_key:
                r = attr.attr_name
        return cast(str, h), r

    @staticmethod
    def _iter_model_indexes(
        model: type['Model'],
    ) -> Generator[tuple[str, str, str | None], None, None]:
        """
        Yields tuples: (index name, hash_key, range_key) indexes of the given
        model. Currently, only global secondary indexes are used so this
        implementation wasn't tested with local ones. Uses private PynamoDB
        API because cannot find public methods that can help
        """
        for index in model._indexes.values():
            name = index.Meta.index_name
            h, r = None, None
            for attr in index.Meta.attributes.values():
                if attr.is_hash_key:
                    h = attr.attr_name
                if attr.is_range_key:
                    r = attr.attr_name
            yield name, cast(str, h), r

    def _iter_all_model_indexes(
        self, model: type['Model']
    ) -> Generator[tuple[str, str, str | None], None, None]:
        yield self._main_index_name, *self._get_hash_range_names(model)
        yield from self._iter_model_indexes(model)

    def sync(self, model: type['Model']) -> None:
        table_name = model.Meta.table_name
        _LOG.info(f'Going to check indexes for {table_name}')
        collection = self._adapter.get_collection(model)
        existing = collection.index_information()
        for name in self._ignore:
            existing.pop(name, None)
        needed = {}
        for name, h, r in self._iter_all_model_indexes(model):
            needed[name] = [(h, self._ho)]
            if r:
                needed[name].append((r, self._ro))
        to_create = []
        to_delete = set()
        for name, data in existing.items():
            if name not in needed:
                to_delete.add(name)
                continue
            # name in needed so maybe the index is valid, and we must keep it
            # or the index has changed, and we need to re-create it
            if data.get('key', []) != needed[name]:  # not valid
                to_delete.add(name)
                to_create.append(IndexModel(keys=needed[name], name=name))
            needed.pop(name)
        for name, keys in needed.items():  # all that left must be created
            to_create.append(IndexModel(keys=keys, name=name))
        for name in to_delete:
            _LOG.info(f'Going to remove index: {name}')
            collection.drop_index(name)
        if to_create:
            _message = ','.join(
                json.dumps(i.document, separators=(',', ':'))
                for i in to_create
            )
            _LOG.info(f'Going to create indexes: {_message}')
            collection.create_indexes(to_create)
