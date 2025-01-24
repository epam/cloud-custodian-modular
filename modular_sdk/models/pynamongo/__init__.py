"""
pynamodb 5.5.1
pymongo 4.10.1

This module provides a way to interact with MongoDB using PynamoDB ORM.
You may assume that not all the features are covered and you would be right.
Yet most useful cases are covered.

First, what you should understand is how PynamoDB models are converted to
MongoDB documents. That is done in two steps:
- call .serialize() method on PynamoDB model
- convert the result from DynamoDB JSON to a dict that can be accepted by
  Mongo (means removing all DynamoDB types: {"S": "value"} -> "value")
The models are converted this way in order to use PynamoDB's serialization code
that handles all maps/lists traversals, correct serialization of each attr
and validation. Respectively, MongoDB documents first converted to
DynamoDB JSON and then .deserialize() method is called.

Second, you must understand that some existing PynamoDB Attributes are
supported immediately while some other require a patch. Those that require the
patch are listed below:
- BinaryAttribute: PynamoDB BinaryAttribute's serialization code does not work
  for Mongo because it serializes to string instead of bytes. Also it makes
  double base64 encoded values
- UTCDateTimeAttribute: it encodes its value to string. This works for Mongo
  but the patched attribute utilizes Mongo "Date" type instead of String.
- UnicodeSetAttribute, NumberSetAttribute, BinarySetAttribute: they do not have
  Mongo analogs so must be emulated.

Patch will be applied only to models that have `mongo_attributes = True` in
their Meta class. To apply the patch you must import a specific function
and call it before models declaration:

    from pynamodb.models import Model
    from pynamodb.attributes import *

    from modular_sdk.models.pynamongo.patch import patch_attributes
    patch_attributes()

    class User(Model):
        class Meta:
            table_name = 'User'
            region = 'eu-west-1'
            mongo_attributes = True

        email = UnicodeAttribute(hash_key=True)
        age = NumberAttribute()
        data = MapAttribute(default=dict)

Note:
- you do not need patch if you not going to use any of attributes that require patch
- patch just replaces necessary attributes with their patched versions that
  could be used only with Mongo afterwards. So you may consider something like:

    from modular_sdk.models.pynamongo.patch import patch_attributes
    if os.getenv('IS_MONGO'):
        patch_attributes()

  or something like:

    class User(Model):
        class Meta:
            mongo_attributes = bool(os.getenv('IS_MONGO'))

Now look at the tables:

Table 1. Mapping of Native DynamoDB types to corresponding Mongo types

Native DynamoDB Type | Corresponding Native Mongo Type
---------------------+-----------------------------
S                    | String
N                    | Double
B                    | Binary
BOOL                 | Boolean
NULL                 | Null
M                    | Object
L                    | Array
SS                   | -
NS                   | -
BS                   | -

Any custom or existing PynamoDB Attribute that uses a Native DynamoDB Type that
has a corresponding Native Mongo Type can be used for Mongo without any code
changes or patches.


Table 2. Describes PynamoDB Attributes and their patches for Mongo if needed

PynamoDB Attribute   | DynamoDB type | Used Mongo type | Patched |
---------------------+---------------+-----------------+---------+
UnicodeAttribute     | S             | String          | NO      |
NumberAttribute      | N             | Double          | NO      |
BinaryAttribute      | B             | Binary          | YES     |
BooleanAttribute     | BOOL          | Boolean         | NO      |
NullAttribute        | NULL          | Null            | NO      |
---------------------+---------------+-----------------+---------+
MapAttribute         | M             | Object          | NO      |
DynamicMapAttribute  | M             | Object          | NO      |
ListAttribute        | L             | Array           | NO      |
---------------------+---------------+-----------------+---------+
UTCDateTimeAttribute | S             | Date            | YES     |
JSONAttribute        | S             | String          | NO      |
---------------------+---------------+-----------------+---------+
UnicodeSetAttribute  | SS            | Array[String]   | YES     |
NumberSetAttribute   | NS            | Array[Number]   | YES     |
BinarySetAttribute   | BS            | Array[Binary]   | YES     |


Usage:
All your existing PynamoDB models can already work with MongoDB. The only
caveat is that UnicodeSetAttribute, NumberSetAttribute, BinarySetAttribute,
BinaryAttribute must not be used. You can take your model and pass it to
PynamoDBToPymongoAdapter to work with Mongo.

    from pynamodb.models import Model
    from pynamodb.attributes import *

    class User(Model):
        class Meta:
            table_name = 'User'
            region = 'eu-west-1'

        email = UnicodeAttribute(hash_key=True)
        age = NumberAttribute()
        data = MapAttribute(default=dict)

    adapter = PynamoDBToPymongoAdapter(db=MongoClient().get_database('db'))
    adapter.save(User(
        email='example@gmail.com',
        age=18,
        data={'key': 'value'}
    ))
    item = next(adapter.query(model=User, hash_key='example@gmail.com'))
    assert item.age == 18 and item.data.as_dict() == {'key': 'value'}
    adapter.delete(item)
    assert not tuple(adapter.scan(model=User))


If you want to use native PynamoDB Methods just inherit the model from our
custom Model type. It has two class methods that should be overridden:
- is_mongo_model(): must return True of False whether to use MongoDB
- mongo_adapter(): must return initialized Mongo Adapter
Default implementations are provided but look them up yourself.

    from modular_sdk.models.pynamongo.models import Model

    class ModularModel(Model):
        @classmethod
        def is_mongo_model(cls) -> bool:
            return bool(os.getenv('USE_MONGO'))

        @classmethod
        def mongo_adapter(cls) -> PynamoDBToPymongoAdapter:
            if hasattr(cls, '_mongo_adapter'):
                return cls._mongo_adapter
            setattr(cls, '_mongo_adapter', PynamoDBToPymongoAdapter(
                db=pymongo.MongoClient(os.getenv('MONGO_URL')).get_database(os.getenv('MONGO_DB'))
            ))
            return getattr(cls, '_mongo_adapter')

    class User(ModularModel):
        class Meta:
            table_name = 'User'
            region = 'eu-west-1'

        email = UnicodeAttribute(hash_key=True)
        age = NumberAttribute()
        data = MapAttribute(default=dict)

    User(email='example@gmail.com', age=18, data={'key': 'value'}).save()
    item = next(User.query(hash_key='example@gmail.com'))
    assert item.age == 18 and item.data.as_dict() == {'key': 'value'}
    item.delete()
    assert not tuple(User.scan())


What private PynamoDB things are used directly:
- pynamodb.expressions.operand._Decrement
- pynamodb.expressions.operand._Increment
- pynamodb.expressions.operand._ListAppend

- pynamodb.models.Model._get_keys()
- pynamodb.models.Model._serialize_keys()
- pynamodb.models.Model._hash_key_attribute()
- pynamodb.models.Model._range_key_attribute()
- pynamodb.models.Model._indexes
- pynamodb.models.Model._instantiate()  if overridden once

Caveats to know:
- NullAttribute from PynamoDB returns None when deserialized and then if you
  try to save the instance it will be just omitted. That is strange. Better
  do not use the NullAttribute or at least use it specifying null=True
  (NullAttribute(null=True))
- DynamicMapping from PynamoDB has strange behavior of a bug. It always
  contains "attribute_values" inside even if you didn't set such attribute.
  That is somehow related to its inner representation. Better not use that
  for now. Standard MapAttribute can easily replace the dynamic one.
- UnicodeSetAttribute, NumberSetAttribute, BinarySetAttribute from PynamoDB are
  emulated for Mongo using arrays of corresponding types. They work for
  simple cases but have some limitations with update/query features and
  obviously do not provide the conveniences of Set data structure.
- BinaryAttribute from PynamoDB 5.5.1 has a bug. Its value is encoded to
  base64 twice. There is an implementation that fixes that
  (modular_sdk.models.pynamongo.attributes.BinaryAttribute). It works both
  for Mongo and DynamoDB and used for Mongo by default.
- Dots ('.') are not supported in attribute names. So check all your attributes
  carefully. If you want to support that replace then wit '|#|'. That will be
  backward-compatible with previous version of modular_sdk

What PynamoDB Update expressions supported for Mongo:

DynamoDB Action | Type       | Supported | Example                                    |
----------------+------------+-----------+--------------------------------------------+
SET             | ANY        | YES       | Model.attr.set('one')                      |
SET             | List item  | YES       | Model.list[0].set(1)                       |
REMOVE          | ANY        | YES       | Model.attr.remove()                        |
REMOVE          | List item  | YES       | Model.list[4].remove()                     |  [WARNIING: with shifting as Dynamo's, but test before using]
ADD             | Number     | YES       | Model.number.add(11)
ADD             | Set        | NO        |                                            |
DELETE          | Set        | NO        |                                            |

LIST APPEND     | List       | YES       | Model.list.set(Model.list.append([1,2,3])) |
LIST PREPEND    | List       | YES       | Model.list.set(Model.list.prepend([1,2]))  |
ADD OTHER ATTR  | Number     | YES       | Model.number.set(Model.map['number'] + 3)  |
IF NOT EXISTS   | Any        | NO        |                                            |


What PynamoDB Condition expressions supported for Mongo:

Expression           | Supported | Example                                        |
---------------------+-----+------------------------------------------------------+
equal (=)            | YES       | Model.string == 'test'                         |
not equal (<>)       | YES       | Model.string != 'test'                         |
gt, lt, gte, lte     | YES       | Model.number <= 10                             |
BETWEEN              | YES       | Model.number.between(10, 20)                   |
IN                   | YES       | Model.map['key'].is_in('one', 'two')           |
attribute_exists     | YES       | Model.list.exists()                            |
attribute_not_exists | YES       | Model.number.does_not_exist()                  |
attribute_type       | NO        |                                                |
begins_with          | YES       | Model.string.startswith('test')                |
contains             | YES       | Model.string.contains('test')                  | [WARNING: not supported for Sets]
size                 | NO        |                                                |
AND                  | YES       | (Model.number > 10) & (Model.string == 'test') |
OR                   | YES       | (Model.number > 10) | (Model.string == 'test') |
NOT                  | YES       | ~(Model.number > 10)                           |

Almost all public methods of Model are supported. Those are:
- batch_get
- batch_write
- delete
- update
- save
- refresh
- get
- count
- query
- scan
- exists
- delete_table
- create_table

What PynamoDB features are not supported:
- Polymorphism through the use of discriminators (https://pynamodb.readthedocs.io/en/stable/polymorphism.html)
- Transaction Operations (https://pynamodb.readthedocs.io/en/stable/transaction.html)
- Conditional writes (https://pynamodb.readthedocs.io/en/stable/conditional.html#conditioning-on-keys)
- Local secondary indexes (https://pynamodb.readthedocs.io/en/stable/indexes.html#local-secondary-indexes)

"""
from .adapter import PynamoDBToPymongoAdapter, ResultIterator
from .attributes import (
    AS_IS,
    BinaryAttribute,
    DynamicAttribute,
    EnumUnicodeAttribute,
    M3BooleanAttribute,
    MongoBinarySetAttribute,
    MongoNumberSetAttribute,
    MongoUnicodeSetAttribute,
    MongoUTCDateTimeAttribute,
    UUIDAttribute,
)
from .convertors import PynamoDBModelToMongoDictSerializer
from .patch import patch_attributes
from .indexes_creator import IndexesCreator

__all__ = (
    'PynamoDBToPymongoAdapter',
    'ResultIterator',
    'AS_IS',
    'BinaryAttribute',
    'DynamicAttribute',
    'EnumUnicodeAttribute',
    'M3BooleanAttribute',
    'MongoBinarySetAttribute',
    'MongoNumberSetAttribute',
    'MongoUnicodeSetAttribute',
    'MongoUTCDateTimeAttribute',
    'UUIDAttribute',
    'PynamoDBModelToMongoDictSerializer',
    'patch_attributes',
    'IndexesCreator'
)
