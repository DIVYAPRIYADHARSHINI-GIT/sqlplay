import sqlite3
import pytest
from fastapi.testclient import TestClient
import main
from engine import Database, QueryError

class NoExtensionBuild(sqlite3.Connection):
    @property
    def enable_load_extension(self):
        raise AttributeError('Extension loading was compiled out')

def test_serverless_without_extension_loading_method(monkeypatch):
    connect = sqlite3.connect
    monkeypatch.setattr(sqlite3, 'connect', lambda *a, **kw: connect(*a, **kw, factory=NoExtensionBuild))
    db = Database()
    assert db.run('SELECT 1')['rows'] == [(1,)]
    with pytest.raises(QueryError):
        db.run("SELECT load_extension('anything')")
    db.keeper.close()

def test_health_exercises_restricted_connection(monkeypatch):
    def unavailable(query):
        raise RuntimeError('A host connection feature is unavailable')
    monkeypatch.setattr(main.database, 'run', unavailable)
    response = TestClient(main.app).get('/health')
    assert response.status_code == 503
    assert response.json()['detail'] == 'The sample database is not ready. Please retry.'
