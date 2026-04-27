import pytest


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    import db
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.init_db()
    return db_path
