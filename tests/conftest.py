import pytest


@pytest.fixture(scope="session")
def master_provider():
    return {"id": 1, "type": "master"}


@pytest.fixture(scope="session")
def consumer_provider():
    return {"id": 2, "type": "consumer"}


@pytest.fixture(scope="session")
def cluster():
    return {"id": 1, "ox_cluster_hostname": "test.example.com"}


@pytest.fixture(scope="session")
def ldap_node(cluster, master_provider):
    return {
        "id": 1,
        "provider_id": master_provider["id"],
        "cluster_id": cluster["id"],
        "state": "SUCCESS",
        "type": "ldap",
        "weave_ip": "10.2.1.1",
    }


@pytest.fixture(scope="session")
def oxauth_node(cluster, master_provider):
    return {
        "id": 2,
        "provider_id": master_provider["id"],
        "cluster_id": cluster["id"],
        "state": "SUCCESS",
        "type": "oxauth",
        "weave_ip": "10.2.1.2",
    }


@pytest.fixture(scope="session")
def oxtrust_node(cluster, master_provider):
    return {
        "id": 3,
        "provider_id": master_provider["id"],
        "cluster_id": cluster["id"],
        "state": "SUCCESS",
        "type": "oxtrust",
        "weave_ip": "10.2.1.3",
        "truststore_fn": "/path",
    }


@pytest.fixture(scope="session")
def httpd_node(cluster, master_provider):
    return {
        "id": 4,
        "provider_id": master_provider["id"],
        "cluster_id": cluster["id"],
        "state": "SUCCESS",
        "type": "httpd",
        "weave_ip": "10.2.1.4",
    }


@pytest.fixture
def db(request, cluster, master_provider, consumer_provider,
       ldap_node, oxauth_node, oxtrust_node, httpd_node):
    import json
    import os
    import tempfile
    from gluuagent.database import Database

    _, database_uri = tempfile.mkstemp(suffix=".json")

    data = {
        "providers": {
            "1": master_provider,
            "2": consumer_provider,
        },
        "clusters": {
            "1": cluster,
        },
        "nodes": {
            "1": ldap_node,
            "2": oxauth_node,
            "3": oxtrust_node,
            "4": httpd_node,
        },
    }
    with open(database_uri, "w") as fp:
        fp.write(json.dumps(data))

    def teardown():
        os.unlink(database_uri)

    db = Database(database_uri)
    request.addfinalizer(teardown)
    return db


@pytest.fixture(scope="session")
def docker_client(request):
    from docker import Client

    client = Client()

    def teardown():
        client.close()

    request.addfinalizer(teardown)
    return client
