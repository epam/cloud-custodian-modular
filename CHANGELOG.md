# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [7.0.0] - 2024-12-18
- Rewritten Pynamo & Mongo abstraction to support all attributes and functionality:
  - `modular_sdk.models.pynamongo.models.Model` must be used instead of old BaseModel (see docs inside `modular_sdk.models.pynamongo.__init__`)
  - `get_json()` is not deprecated and will be removed. Use pynamongo.convertors.instance_to_dict or write your serializer
  - `mongo_id` attribute was replaced with `__mongo_id__`
- Updated `pymongo` version to `pymongo~=4.10.1`
- Removed `dynamodb-json~=1.4.2` package
- Removed variables, functions, classes and modules:
  - `modular_sdk.commons.DynamoDBJsonSerializer`
  - `modular_sdk.commons.build_response`
  - `modular_sdk.commons.RESPONSE_*`
  - `modular_sdk.commons.dict_without`
  - `modular_sdk.commons.error_helper`
  - `modular_sdk.commons.deep_pop`
  - `modular_sdk.helpers`
  - `modular_sdk.models.pynamodb_extension`
  - `modular_sdk.connections.mongodb_connection`
- Added:
  - `modular_sdk.models.pynamongo.index_creator.IndexCreator`

## [6.3.0] - 2024-11-26
- Fix Vault parameters encoder to comply with Maestro format
- Update `get_signed_headers` to support conditional handling of `http` and
`rabbit` specific headers

## [6.2.1] - 2024-10-18
- Update `Modular` and `MaestroHTTPTransport` classes
- Add `MaestroHTTPConfig` class
- Improved logging

## [6.2.0] - 2024-10-04
- added `MaestroHTTPTransport` to allow to interact with maestro using https protocol

## [6.1.1] - 2024-10-04
- added `MODULAR_SDK_HTTP_PROXY` and `MODULAR_SDK_HTTPS_PROXY` envs

## [6.1.0] - 2024-09-13
- Update `pika` library from version `1.0.0b1` to `1.3.2`
- Update `RabbitMqConnection` class to support `pika` version `1.3.2`
- Replace `uuid1` with `uuid4`
- Up lib version to `pynamodb==5.5.1` and `dynamodb-json~=1.4.2`

## [6.0.1b2] - 2024-09-12
- Dump lib version to `pynamodb==5.3.2` and `dynamodb-json~=1.3`

## [6.0.1b1] - 2024-09-11
- fix rabbitmq bug when a wrong message was consumed after pushing

## [6.0.0] - 2024-08-20
- Split `SIEM_DEFECT_DOJO` Parent type into:
  - CUSTODIAN_SIEM_DEFECT_DOJO
  - RIGHTSIZER_SIEM_DEFECT_DOJO

## [5.1.7] - 2024-08-20
- added more logs for RabbitMQ connection
- rollback `pika` to fix breaking changes

## [5.1.6] - 2024-08-19
- remove usage of `accN` index for Tenants model. Proxy old methods and attributes to `acc` index

## [5.1.5] - 2024-07-29
- fix `pynamodb` non compatible changes

## [5.1.4] - 2024-07-18
- removed setup.cfg and setup.py. Used pyproject.toml instead.
- changed libs versions to more flexible

## [5.1.3] - 2024-06-09
- added new Application and Parent type: "GCP_CHRONICLE_INSTANCE"

## [5.1.2] - 2024-05-13
- try to load json from vault str values

## [5.1.1] - 2024-03-12
- add pyright config to pyproject.toml
- add values preprocessor to pynamodb_to_pymongo_adapter instead of using 
  workaround with dumping-loading json
- added `is_active` to Customer model
- added `deactivation_date` to Tenant model
- added some additional parameters to ApplicationService.list method
- added some parameters to CustomerService.i_get_customer method
- added some parameters to TenantService.i_get_by_tenant method
- fixe the supported Python versions in README.md and setup.cfg files

## [5.1.0] - 2024-02-13
- Added customer settings and customer settings service

## [5.0.3] - 2024-01-31
- removed `boltons` from requirements

## [5.0.2] - 2024-01-31
- add more parameters to `parent_service.i_list_application_parents` method

## [5.0.1] - 2024-01-26
- fix last_evaluted_key calculating in PynamoTOMondoDBAdapter

## [5.0.0] - 2024-01-25
- Application: switch to using cid-t-index (customer_id/type) from cid-index (customer_id)

## [4.0.3] - 2024-01-24
- Parent service: switch to using application_id index instead of scans

## [4.0.2] - 2024-01-18
- Fix `ct` (creation_timestamp) to store as an int in `Parent` table

## [4.0.1] - 2024-01-15
- Fix `dt` (deletion_timestamp) to store as an int in `Application` and `Parent` tables

## [4.0.0] - 2024-01-11
- Change the models in Python to match the models in Java. Table names:
  * `Application`:
    * Added: `ub` (updated by), `cb`(created by)
  * `Parents`:
    * Added: `ub` (updated by), `cb`(created by)
- Update the logic when creating `Application` and `Parents` items. New fields `ub`
and `cb` are required.

## [3.3.11] - 2023-10-26
- add dry run mode message in meta field when starting job tracer if there is
`dry_run` attribute in event

## [3.3.10] - 2023-12-14
- add optional `consistent_read` argument to the `get_nullable` function
- add the ability to set `component` of `job_tracer` decorator also manually via an argument

## [3.3.9] - 2023-12-08
- add methods for force deletion of Application/Parent

## [3.3.8] - 2023-11-28
- add `RIGHTSIZER_LICENSES` application type

## [3.3.7] - 2023-11-28
- do not scan parents when we remove application

## [3.3.6] - 2023-11-14
- remove K8S application meta dataclass because it's empty

## [3.3.5] - 2023-11-13
- remove not used `K8S_SERVICE_ACCOUNT` application type

## [3.3.4] - 2023-11-13
- fix page size in PynamoToMongoDBAdapter

## [3.3.3] - 2023-11-02
- add `tenant_name` to Parent dto

## [3.3.2] - 2023-10-16
- minor fixes

## [3.3.1] - 2023-10-16
- removed `cid-index` from Parent model

## [3.3.0] - 2023-09-12
- redid mark_deleted in application_service & parent_service. Now these 
  methods update items in DB. You don't need to call .save() afterwards
- added (temporarily ethereal) application_id index to parent. It's currently 
  not used because it does not exist in DB but once it's added to DB it 
  should be immediately taken to advantage of
- added `cid-s-index` (customer_id, scope) index to Parent model. It's used 
  in order to adjust connections between tenants and parents
- added new public methods to parent_service which use `cid-s-index`:
  - create_all_scope
  - create_tenant_scope
  - get_by_tenant_scope
  - get_by_all_scope
  - get_linked_parent_by_tenant
  - get_linked_parent
  
  and some other methods though they're not that "high level"
- added `deprecated` decorator to mark methods that should not be used

## [3.2.0] - 2023-10-03
- Requests signature changed(maestro-user-identifier added to the signature)

## [3.1.0] - 2023-10-03
- Added ThreadLocalStorageService

## [3.0.0] - 2023-09-26
- Added Python 3.10 compatibility
- Updated libraries version
- File setup.cfg brought to compatibility with new setuptools syntax

## [2.2.6] - 2023-09-20
- integrated job service into modular job tracer
- handle Decimal for on-prem update recursively

## [2.2.5] - 2023-09-20
- added `limit` attribute to `i_get_by_tenant` and `i_get_by_key` 
  methods for tenant_settings_service;
- added method `get` to tenant_settings_service
- create an item in MongoDB in case it does not exist after performing .update

## [2.2.4] - 2023-09-19
- Fix unhandled exception in `get_by_id` method in `JobService`

## [2.2.3] - 2023-09-11
- Fix an issue related to bug in encrypt method in case if parameter was not passed
- Fix an issue related to bug in get_signed_headers method in case if parameter was not passed
- Add `JobService`

## [2.2.2] - 2023-08-29
- Fix update action for PynamoTOMondoDBAdapter. Now if you use update, the 
  python instance will be updated as well.
- fix save method for batch_write for PynamoTOMondoDBAdapter
- Fix PynamoTOMondoDBAdapter.count action. Now it can accept
  filter_condition and range_key_condition
- Fix attributes_to_get (UnicodeAttribute is not hashable)

## [2.2.1] - 2023-08-07
- Fix a bug with PynamoTOMondoDBAdapter startswith condition
- add `separators=(",", ":")` to json.dumps to make the payload a bit smaller

## [2.2.0] - 2023-08-03
- add `RIGHTSIZER_LICENSES` parent type
- add `RIGHTSIZER_LICENSES` parent `pid` map key
- add `cloud` and `rate_limit` parameters to 
  `tenant_service.i_get_tenant_by_customer()`

## [2.1.6] - 2023-08-03
- Add `CUSTODIAN_ACCESS` parent type and `CUSTODIAN_ACCESS` tenant parent map 
  type
- Fix a bug when range_key_conditions for NumberAttributes did not work for MongoDB
- Fix google credentials project id
- added `job-started_at-index` GSI to the `ModularJobs` table

## [2.1.5] - 2023-07-26
- Application and Parent models were updated with new attributes:
  - creation timestamp - `ct`
  - update timestamp - `ut`
  - deletion timestamp - `dt`

## [2.1.4] - 2023-06-30
- Update setup.cfg

## [2.1.3] - 2023-06-22
- RabbitMQApplicationMeta: change config user key to `maestro_user`

## [2.1.2] - 2023-06-21
- MaestroRabbitMQTransport: change config user key to `maestro_user`

## [2.1.1] - 2023-06-21
- imports unification: update imports to use `modular_sdk` as a root

## [2.1.0] - 2023-06-14
- fix a bug with mongoDB specific types in PynamoToMongoDB adapter. 
  Now method `from_json` performs the full deep deserialization of MongoDB 
  json the same way it does it to DynamoDB JSON. Unknown types will be proxied.

## [2.0.2] - 2023-05-29
- add `AccessMeta` class which declares common model for access data to 
  another api. It contains host, port, schema and path prefix.

## [2.0.1] - 2023-05-22
- added support of applications with type `RABBITMQ`. Added code to resolve 
  credentials for such application to maestro_credentials_service.
- tenant id is returned in `account_id` attribute instead of `project` in method `get_dto`;
- Add boolean validation for settings with `_ARE_` part in setting name
- Add integer validation for settings which ends with `_LONG` or `_INT`

## [2.0.0] - 2023-05-09
- redundant API of services for the following entities was removed: Application, Parent, Tenant, Region, Customer 

## [1.4.5] - 2023-05-04
- add an ability to assume a chain of roles before querying DynamoDB and SSM. 
  Now `modular_assume_role_arn` can contain a list or role arns, split by `,`
- rewrite `BaseSafeUpdateModel` so that it could handle nested map and 
  list attributes;
- implement `update` for `PynamoToMongoDbAdapter`

## [1.4.4] - 2023-05-03
- deem all the regions where `act` attribute is absent - active within an 
  active tenant
- add an ability to use dynamic account id for applications with type AWS_ROLE

## [1.4.3] - 2023-04-24
- added ability to send a batch of requests 

## [1.4.2] - 2023-04-20
- rework encryption and decryption flow for interaction with M3 Server via RabbitMQ

## [1.4.1] - 2023-04-19
- fixed sqs service: in case `queue_url` is not set to envs a message will 
  not be sent. A warning will be shown;

## [1.4.0] - 2023-04-10
- added `maestro_credentials_service` to retrieve credentials from 
  Maestro Applications;
- added `EnvironmentContext` class to export some environment variables 
  temporarily;

## [1.3.14] - 2023-04-07
- add more parameters to `i_get_parent_by_customer`: `is_deleted`, 
  `meta_conditions`, `limit`, `last_evaluted_key`;
- added `get_parent_id` to `Tenant` model;

## [1.3.13] - 2023-04-05
- add setting deletion date (`dd`) on parent/application delete
- remove conditions converted from PynamoToMongoDBAdapter and write a
  new one which supports all the existing conditions from PynamoDB as
  well as nested attributes.

## [1.3.12] - 2023-03-31
- tenant_service: implement methods to add/remove parent id from 
  tenant parent map (pid)
- add limit and last_evaluated_key attrs to get_tenants_by_parent_id. 
  Optimize parent_service.delete

## [1.3.11] - 2023-03-27
- rework validations for setting service in add/update actions

## [1.3.10] - 2023-03-24
- add `RIGHTSIZER` type to list of supported types of Parent 
- update dependency versions

## [1.3.9] - 2023-03-22
- add `RIGHTSIZER` type to list of supported types of Application 

## [1.3.8] - 2023-03-22
- add `MODULARJobs` table 

## [1.3.7] - 2023-03-21
- fix a bug associated with incorrect group name resolving for setting service

## [1.3.6] - 2023-03-17
- compress message if `compressed` parameter in `_build_message` method is `True`

## [1.3.5] - 2023-03-16
- hide `is_permitted_to_start` check before writing to `Jobs` table
- make `compressed` parameter in `pre_process_request` function optional 

## [1.3.4] - 2023-03-14
- add ability to specify `compressed` header for requests with zipped data
- add `attributes_to_get` param to `i_get_by_dntl` and `i_get_by_acc` functions

## [1.3.3] - 2023-02-22
- add ability to manage Settings collection items via setting service 
- Add log events into rabbit_transport service
- Raise version of the `cryptography` library: 3.4.7 -> 39.0.1

## [1.3.2] - 2023-02-01
- add ability to interact with Maestro server via remote execution service
- refactored a bit, added missing attributes to Application model. 
  Added `ModularAssumeRoleClient` descriptor which simulates boto3 client but 
  uses temp credentials obtained by assuming modular_assume_role_arn;
- Fix bugs with tenants, add an alternative method to create region
  (which does not perform full table scan) (currently experimental, used only by Custodian)
- Remove inner instance from `MODULAR` and use SingletonMeta. This makes to
  code clearer and IDEA hints work
- Added `get_region_by_native_name` to region service;

## [1.3.1] - 2023-01-16
- fix resolving of nested MapAttributes where Python's var name differs from 
  attribute's `attr_name` parameter for Tenant model in MongoDB;
- add `contacts`, `DisplayNameToLowerCloudIndex`, `ProjectIndex` to Tenants model


## [1.3.0] - 2022-12-13
- Add util to trace Jobs execution result 
- Add util to trace Runtime/ScheduleRuntime segment execution result

## [1.2.0] - 2022-11-22
- fix limit and last evaluated key in PynamoDBToPymongoAdapter and refactor a bit
- add `limit` and `last_evaluated_key` params to `i_get_tenant_by_customer` 
  and `scan_tenants` methods in tenant service;
- refactor `BaseModel` and add an ability for potential users of SDK to 
  use the PynamoToMongoAdapter and BaseModel from SDK, providing their 
  MongoDB credentials and url

## [1.1.1] - 2022-11-09
- fixed expiration in cross-account access;
- added `classproperty` decorator to helpers;
- added new possible env `modular_AWS_REGION`. It has priority over `AWS_REGION` 
  and can be useful if MODULAR Tables are situated in a different region from 
  the tool that uses MODULAR SDK;
- added functions `utc_iso` and `utc_datetime` instead of `get_iso_timestamp`;

## [1.1.0] - 2022-11-04
- added `customer_id` - `type` index to `Application` model;
- added `key` - `tenant_name` index to `TenantSettings` model;
- added `CUSTODIAN:CUSTOMER` to the list of available Parent types;
- Made `modular.models.pynamodb_extension.pynamodb_to_pymongo_adapter.Result` 
  iterator instead of list;
- updated `pynamodb` version to `5.2.3`;
- fixed bugs with tenant regions;
- added some method to services to query entities in different ways;

## [1.0.0] - 2022-10-03

### Added
    -  Initial version of Modular SDK.

