def test_database_get(db):
    assert db.get(1, "providers")["type"] == "master"


def test_database_all(db):
    assert len(db.all("providers")) == 2


def test_database_search(db):
    result = db.search_from_table("providers", db.where("type") == "master")
    assert len(result) == 1
