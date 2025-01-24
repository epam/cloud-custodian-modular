import pymongo
from datetime import datetime
import json
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Text,
    Union,
)

from pynamodb.attributes import Attribute, ListAttribute, MapAttribute
from pynamodb.connection.table import TableConnection
from pynamodb.exceptions import DoesNotExist
from pynamodb.expressions.condition import Condition
from pynamodb.expressions.update import Action
from pynamodb.models import _T, BatchWrite, _KeyType
from pynamodb.models import Model as _Model
from pynamodb.pagination import ResultIterator
from pynamodb.settings import OperationSettings

from modular_sdk.commons.constants import Env, SERVICE_MODE_DOCKER
from modular_sdk.commons.log_helper import get_logger
from modular_sdk.models.pynamongo.adapter import PynamoDBToPymongoAdapter
from modular_sdk.modular import Modular
from modular_sdk.commons.time_helper import utc_iso
from modular_sdk.commons import deprecated, iter_subclasses

_LOG = get_logger(__name__)


class ModelEncoder(json.JSONEncoder):
    """
    It converts the item to DTO only representation. Do not use
    get_json() on model and then write the result to DB again. Such
    actions corrupt the item
    """

    def default(self, obj):
        if hasattr(obj, 'attribute_values'):
            return obj.attribute_values
        elif isinstance(obj, datetime):
            return utc_iso(_from=obj)
        else:
            # ObjectId, bytes and others
            return str(obj)
        # return json.JSONEncoder.default(self, obj)


class Model(_Model):
    @classmethod
    def mongo_adapter(cls) -> PynamoDBToPymongoAdapter:
        if hasattr(cls, '_mongo_adapter'):
            return getattr(cls, '_mongo_adapter')
        setattr(cls, '_mongo_adapter', PynamoDBToPymongoAdapter())
        return getattr(cls, '_mongo_adapter')

    @classmethod
    def is_mongo_model(cls) -> bool:
        return (
            getattr(cls.Meta, 'mongo_database', None) is not None
            or getattr(cls.Meta, 'mongo_collection', None) is not None
        )

    @classmethod
    def batch_get(
        cls,
        items: Iterable[Union[_KeyType, Iterable[_KeyType]]],
        consistent_read: Optional[bool] = None,
        attributes_to_get: Optional[Sequence[str]] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> Iterator[_T]:
        if cls.is_mongo_model():
            return cls.mongo_adapter().batch_get(
                model=cls, items=items, attributes_to_get=attributes_to_get
            )
        return super().batch_get(
            items=items,
            consistent_read=consistent_read,
            attributes_to_get=attributes_to_get,
            settings=settings,
        )

    @classmethod
    def batch_write(
        cls,
        auto_commit: bool = True,
        settings: OperationSettings = OperationSettings.default,
    ) -> BatchWrite[_T]:
        if cls.is_mongo_model():
            return cls.mongo_adapter().batch_write(model=cls)
        return super().batch_write(auto_commit=auto_commit, settings=settings)

    def delete(
        self,
        condition: Optional[Condition] = None,
        settings: OperationSettings = OperationSettings.default,
        *,
        add_version_condition: bool = True,
    ) -> Any:
        if self.is_mongo_model():
            return self.mongo_adapter().delete(instance=self)
        return super().delete(
            condition=condition,
            settings=settings,
            add_version_condition=add_version_condition,
        )

    def update(
        self,
        actions: List[Action],
        condition: Optional[Condition] = None,
        settings: OperationSettings = OperationSettings.default,
        *,
        add_version_condition: bool = True,
    ) -> Any:
        if self.is_mongo_model():
            return self.mongo_adapter().update(instance=self, actions=actions)
        return super().update(
            actions=actions,
            condition=condition,
            settings=settings,
            add_version_condition=add_version_condition,
        )

    def save(
        self,
        condition: Optional[Condition] = None,
        settings: OperationSettings = OperationSettings.default,
        *,
        add_version_condition: bool = True,
    ) -> Dict[str, Any]:
        if self.is_mongo_model():
            return self.mongo_adapter().save(instance=self)
        return super().save(
            condition=condition,
            settings=settings,
            add_version_condition=add_version_condition,
        )

    def refresh(
        self,
        consistent_read: bool = False,
        settings: OperationSettings = OperationSettings.default,
    ) -> None:
        if self.is_mongo_model():
            return self.mongo_adapter().refresh(instance=self)
        return super().refresh(
            consistent_read=consistent_read, settings=settings
        )

    @classmethod
    def get(
        cls,
        hash_key: _KeyType,
        range_key: Optional[_KeyType] = None,
        consistent_read: bool = False,
        attributes_to_get: Optional[Sequence[Text]] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> _T:
        if cls.is_mongo_model():
            return cls.mongo_adapter().get(
                model=cls,
                hash_key=hash_key,
                range_key=range_key,
                attributes_to_get=attributes_to_get,
            )
        return super().get(
            hash_key=hash_key,
            range_key=range_key,
            consistent_read=consistent_read,
            attributes_to_get=attributes_to_get,
            settings=settings,
        )

    @classmethod
    def get_nullable(
        cls,
        hash_key: _KeyType,
        range_key: Optional[_KeyType] = None,
        consistent_read: bool = False,
        attributes_to_get: Optional[Sequence[Text]] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> _T | None:
        try:
            return cls.get(
                hash_key=hash_key,
                range_key=range_key,
                consistent_read=consistent_read,
                attributes_to_get=attributes_to_get,
                settings=settings,
            )
        except DoesNotExist:
            return

    @classmethod
    def count(
        cls,
        hash_key: Optional[_KeyType] = None,
        range_key_condition: Optional[Condition] = None,
        filter_condition: Optional[Condition] = None,
        consistent_read: bool = False,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        rate_limit: Optional[float] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> int:
        if cls.is_mongo_model():
            return cls.mongo_adapter().count(
                model=cls,
                hash_key=hash_key,
                range_key_condition=range_key_condition,
                filter_condition=filter_condition,
                index_name=index_name,
                limit=limit,
            )
        return super().count(
            hash_key=hash_key,
            range_key_condition=range_key_condition,
            filter_condition=filter_condition,
            consistent_read=consistent_read,
            index_name=index_name,
            limit=limit,
            rate_limit=rate_limit,
            settings=settings,
        )

    @classmethod
    def query(
        cls,
        hash_key: _KeyType,
        range_key_condition: Optional[Condition] = None,
        filter_condition: Optional[Condition] = None,
        consistent_read: bool = False,
        index_name: Optional[str] = None,
        scan_index_forward: Optional[bool] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Dict[str, Any]]] = None,
        attributes_to_get: Optional[Iterable[str]] = None,
        page_size: Optional[int] = None,
        rate_limit: Optional[float] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> ResultIterator[_T]:
        if cls.is_mongo_model():
            return cls.mongo_adapter().query(
                model=cls,
                hash_key=hash_key,
                range_key_condition=range_key_condition,
                filter_condition=filter_condition,
                index_name=index_name,
                scan_index_forward=scan_index_forward,
                limit=limit,
                last_evaluated_key=last_evaluated_key,
                attributes_to_get=attributes_to_get,
                page_size=page_size,
            )
        return super().query(
            hash_key=hash_key,
            range_key_condition=range_key_condition,
            filter_condition=filter_condition,
            consistent_read=consistent_read,
            index_name=index_name,
            scan_index_forward=scan_index_forward,
            limit=limit,
            last_evaluated_key=last_evaluated_key,
            attributes_to_get=attributes_to_get,
            page_size=page_size,
            rate_limit=rate_limit,
            settings=settings,
        )

    @classmethod
    def scan(
        cls,
        filter_condition: Optional[Condition] = None,
        segment: Optional[int] = None,
        total_segments: Optional[int] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Dict[str, Any]]] = None,
        page_size: Optional[int] = None,
        consistent_read: Optional[bool] = None,
        index_name: Optional[str] = None,
        rate_limit: Optional[float] = None,
        attributes_to_get: Optional[Sequence[str]] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> ResultIterator[_T]:
        if cls.is_mongo_model():
            return cls.mongo_adapter().scan(
                model=cls,
                filter_condition=filter_condition,
                limit=limit,
                last_evaluated_key=last_evaluated_key,
                page_size=page_size,
                index_name=index_name,
                attributes_to_get=attributes_to_get,
            )
        return super().scan(
            filter_condition=filter_condition,
            segment=segment,
            total_segments=total_segments,
            limit=limit,
            last_evaluated_key=last_evaluated_key,
            page_size=page_size,
            consistent_read=consistent_read,
            index_name=index_name,
            rate_limit=rate_limit,
            attributes_to_get=attributes_to_get,
            settings=settings,
        )

    @classmethod
    def exists(cls) -> bool:
        if cls.is_mongo_model():
            return cls.mongo_adapter().exists(cls)
        return super().exists()

    @classmethod
    def delete_table(cls) -> Any:
        if cls.is_mongo_model():
            return cls.mongo_adapter().delete_table(cls)
        return super().delete_table()

    @classmethod
    def describe_table(cls) -> Any:
        if cls.is_mongo_model():
            raise NotImplementedError('Describe not implemented for mongo')
        return super().describe_table()

    @classmethod
    def create_table(
        cls,
        wait: bool = False,
        read_capacity_units: Optional[int] = None,
        write_capacity_units: Optional[int] = None,
        billing_mode: Optional[str] = None,
        ignore_update_ttl_errors: bool = False,
    ) -> Any:
        if cls.is_mongo_model():
            return cls.mongo_adapter().create_table(cls)
        return super().create_table(
            wait=wait,
            read_capacity_units=read_capacity_units,
            write_capacity_units=write_capacity_units,
            billing_mode=billing_mode,
            ignore_update_ttl_errors=ignore_update_ttl_errors,
        )

    @deprecated('Use modular_sdk.models.pynamongo.convertors.instance_as_* '
                'functions or write your serializer. This one is kept for '
                'easier transition')
    def get_json(self) -> dict:
        """
        Returns dict which can be dumped to JSON. So, in case the model
        contains Date or Binary, or ObjectId -> they will become strings.
        :return:
        """
        return json.loads(json.dumps(self, cls=ModelEncoder))


class SafeUpdateModel(Model):
    """
    Allows not to override existing attributes that are not specified
    in Models on item update.
    """

    _original_data_attr_name = '_original_data'

    @classmethod
    def _update_with_not_defined_attributes(
        cls,
        serialized: dict[str, dict[str, Any]],
        original: dict[str, dict[str, Any]],
        attributes: dict[str, Attribute],
    ) -> None:
        """
        Changes serialized dict in place
        """
        name_to_instance = {
            attr.attr_name: attr for attr in attributes.values()
        }
        for name, value in original.items():
            if name not in name_to_instance:  # not defined in model
                serialized[name] = value
                continue
            # attribute is defined, but maybe it's a nested mapping and
            # some nested attributes are not defined
            attr = name_to_instance[name]
            if isinstance(attr, MapAttribute) and not attr.is_raw():
                cls._update_with_not_defined_attributes(
                    serialized=serialized[name].setdefault(attr.attr_type, {}),
                    original=value.get(attr.attr_type, {}),
                    attributes=attr.get_attributes(),
                )
            elif (
                isinstance(attr, ListAttribute)
                and issubclass(attr.element_type, MapAttribute)
                and not attr.element_type.is_raw()
            ):
                # here we definitely have list of mappings
                inner_attributes = attr.element_type.get_attributes()
                orig_items = value.get(attr.attr_type, ())
                for i, item in enumerate(
                    serialized[name].setdefault(attr.attr_type, [])
                ):
                    if i >= len(orig_items):
                        break
                    cls._update_with_not_defined_attributes(
                        serialized=item.setdefault(
                            attr.element_type.attr_type, {}
                        ),
                        original=orig_items[i].get(
                            attr.element_type.attr_type, {}
                        ),
                        attributes=inner_attributes,
                    )

    def serialize(self, null_check: bool = True) -> dict[str, dict[str, Any]]:
        """
        Used both by Mongo and PynamoDB serializers
        """
        serialized = super().serialize(null_check=null_check)
        self._update_with_not_defined_attributes(
            serialized=serialized,
            original=getattr(self, self._original_data_attr_name, {}),
            attributes=self.get_attributes(),
        )
        return serialized

    def deserialize(self, attribute_values: dict[str, dict[str, Any]]) -> None:
        """
        Used by Mongo deserializer
        """
        setattr(self, self._original_data_attr_name, attribute_values)
        return super().deserialize(attribute_values=attribute_values)

    @classmethod
    def _instantiate(cls, attribute_values: dict[str, dict[str, Any]]):
        """
        Used by PynamoDB deserializer
        """
        instance = super()._instantiate(attribute_values)
        setattr(instance, cls._original_data_attr_name, attribute_values)
        return instance


class RoleAccessModel(SafeUpdateModel):
    """
    Each inherited model will use creds received by assuming a role from
    env variables, and if the creds expire, they will be received again.
    Use custom modular_sdk.models.base_meta.BaseMeta instead of standard Meta in
    the inherited models
    Not highly critical but still - problems:
    - only one role available (the one from envs);
    - if role is set in envs, hard-coded aws keys from Model.Meta/BaseMeta
      will be ignored;
    Take all this into consideration, use BaseRoleAccessModel and BaseMeta
    together.
    """

    @classmethod
    def _get_connection(cls) -> TableConnection:
        _modular = Modular()
        sts = _modular.sts_service()
        if sts.assure_modular_credentials_valid():
            env = _modular.environment_service()
            for model in iter_subclasses(RoleAccessModel):
                if model._connection:
                    # works as well but seems too tough
                    # model._connection = None
                    _LOG.warning(
                        f'Existing connection found in {model.__name__}. '
                        f'Updating credentials in botocore session and '
                        f'dropping the existing botocore client...'
                    )
                    model._connection.connection.session.set_credentials(
                        env.modular_aws_access_key_id(),
                        env.modular_aws_secret_access_key(),
                        env.modular_aws_session_token(),
                    )
                    model._connection.connection._client = None
                else:
                    _LOG.info(
                        f'Existing connection not found in {model.__name__}'
                        f'. Probably the first request. Connection will be '
                        f'created using creds from envs which '
                        f'already have been updated'
                    )
        return super()._get_connection()


class ModularBaseModel(RoleAccessModel):
    @classmethod
    def is_mongo_model(cls) -> bool:
        return Env.OLD_SERVICE_MODE.get() == SERVICE_MODE_DOCKER

    @classmethod
    def mongo_adapter(cls) -> PynamoDBToPymongoAdapter:
        if hasattr(cls, '_mongo_adapter'):
            return cls._mongo_adapter
        user = Env.OLD_MONGO_USER.get()
        password = Env.OLD_MONGO_PASSWORD.get()
        url = Env.OLD_MONGO_URL.get()
        db = Env.OLD_MONGO_DB_NAME.get()
        setattr(cls, '_mongo_adapter', PynamoDBToPymongoAdapter(
            db=pymongo.MongoClient(
                f'mongodb://{user}:{password}@{url}/'
            ).get_database(db)
        ))
        return getattr(cls, '_mongo_adapter')
