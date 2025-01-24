import mongomock
import pytest


@pytest.fixture()
def mongo_client() -> mongomock.MongoClient:
    client = mongomock.MongoClient()
    yield client
    for db in client.list_database_names():
        client.drop_database(db)


@pytest.fixture()
def mongo_database(mongo_client) -> mongomock.Database:
    return mongo_client.get_database('testing')


@pytest.fixture()
def mongo_collection(mongo_database) -> mongomock.Collection:
    return mongo_database.get_collection('testing')
