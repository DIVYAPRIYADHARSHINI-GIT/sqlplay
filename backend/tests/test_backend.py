import sqlite3
import time
import pytest
from fastapi.testclient import TestClient
from engine import Database, CHALLENGES, TABLES, QueryError, compare, RateLimiter
import main

@pytest.fixture(scope='module')
def db():
    return Database()

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, 'limiter', RateLimiter(1000))
    return TestClient(main.app)

BLOCKED = [
    'SELECT 1; SELECT 2', 'SELECT 1; DROP TABLE customers', 'DELETE FROM customers',
    'UPDATE customers SET name=\'x\'', 'INSERT INTO customers(id) VALUES(99)',
    'CREATE TABLE test(x)', 'DROP TABLE products', 'ALTER TABLE products ADD x TEXT',
    'PRAGMA table_info(customers)', 'ATTACH DATABASE \'/tmp/test\' AS x', 'DETACH x',
    'VACUUM', 'REINDEX', 'BEGIN', 'COMMIT', 'EXPLAIN SELECT 1',
    'WITH t AS (SELECT 1) DELETE FROM customers', 'SELECT load_extension(\'x\')',
    'SELECT * FROM sqlite_master', 'SELECT * FROM pragma_table_info(\'customers\')',
    'SELECT readfile(\'/etc/passwd\')', 'SELECT writefile(\'/tmp/x\',\'x\')',
    'SELECT randomblob(999999999)', 'SELECT zeroblob(999999999)', 'SELECT 1\x00',
]
@pytest.mark.parametrize('query', BLOCKED)
def test_safety(db, query):
    with pytest.raises(QueryError):
        db.run(query)

@pytest.mark.parametrize('query', ['SELECT 1', '-- comment\nSELECT 1;', '/* SELECT; */ WITH t AS (SELECT 1 AS n) SELECT n FROM t', "SELECT 'a;b'", "SELECT 'DROP TABLE x'", 'SELECT 1; -- tail'])
def test_allowed(db, query):
    assert db.run(query)['row_count'] == 1

def test_underlying_connection_really_readonly(db):
    con = sqlite3.connect(db.uri + '&mode=ro', uri=True)
    with pytest.raises(sqlite3.OperationalError, match='readonly'):
        con.execute('DELETE FROM customers')
    con.close()

def test_slow_recursive_query(db):
    start = time.perf_counter()
    with pytest.raises(QueryError, match='too long'):
        db.run('WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n) SELECT SUM(x) FROM n')
    assert time.perf_counter() - start < 2

def test_cross_join_timeout(db):
    with pytest.raises(QueryError, match='too long'):
        db.run('SELECT COUNT(*) FROM order_items a,order_items b,order_items c,order_items d,order_items e,order_items f')

def test_result_limit(db):
    with pytest.raises(QueryError, match='500'):
        db.run('SELECT a.id FROM order_items a CROSS JOIN order_items b')

@pytest.mark.parametrize('query', ['', ' ', 'SELECT ' + '1' * 8000])
def test_length(db, query):
    with pytest.raises(QueryError):
        db.run(query)

def test_seed(db):
    assert {t['name'] for t in db.schema} == TABLES
    assert db.keeper.execute('PRAGMA foreign_key_check').fetchall() == []
    assert db.run('SELECT COUNT(*) FROM order_items')['rows'] == [(42,)]
    assert db.run('SELECT COUNT(*) FROM customers WHERE email IS NULL')['rows'][0][0] == 4
    assert db.run('SELECT COUNT(*) FROM orders WHERE customer_id IS NULL')['rows'] == [(1,)]
    assert db.run('SELECT COUNT(*) FROM products WHERE stock=0')['rows'] == [(2,)]

def test_seed_deterministic(db):
    second = Database()
    for t in TABLES:
        assert db.run('SELECT * FROM ' + t)['rows'] == second.run('SELECT * FROM ' + t)['rows']
    second.keeper.close()

def test_catalog():
    assert len(CHALLENGES) >= 40
    assert len({c['id'] for c in CHALLENGES}) == len(CHALLENGES)
    assert {c['level'] for c in CHALLENGES} == {'Easy','Medium','Hard'}
    for c in CHALLENGES:
        assert len(c['hints']) == 3 and len(c['statement']) > 30

@pytest.mark.parametrize('c', CHALLENGES, ids=lambda c: c['id'])
def test_reference_solution(db, c):
    result = db.run(c['solution'])
    assert result['row_count'] > 0
    assert compare(result, db.run(c['solution']), c['ordered'])['correct']

@pytest.mark.parametrize('c', CHALLENGES, ids=lambda c: c['id'])
def test_deliberately_wrong_solution(db, c):
    assert not compare(db.run('SELECT NULL WHERE 0'), db.run(c['solution']), c['ordered'])['correct']

def result(rows, names=None):
    return {'columns': names or ['x'] * (len(rows[0]) if rows else 1), 'rows': rows}

@pytest.mark.parametrize('a,b,ordered,correct,kind', [
    ([[1],[2]], [[2],[1]], False, True, 'correct'),
    ([[1],[2]], [[2],[1]], True, False, 'values_or_order'),
    ([[1],[1]], [[1],[2]], False, False, 'values'),
    ([[1.0000001]], [[1]], False, True, 'correct'),
    ([[1.1]], [[1]], False, False, 'values'),
    ([[None]], [['NULL']], False, False, 'values'),
    ([[None]], [[None]], False, True, 'correct'),
    ([['1']], [[1]], False, False, 'values'),
    ([[1,2]], [[2,1]], False, False, 'values'),
    ([[1]], [[1],[2]], False, False, 'rows'),
    ([[1,2]], [[1]], False, False, 'columns'),
    ([[0.0000009],[0]], [[0],[0.0000018]], False, True, 'correct'),
])
def test_comparator(a,b,ordered,correct,kind):
    checked = compare(result(a), result(b), ordered)
    assert checked['correct'] == correct and checked['kind'] == kind

def test_alias_ignored():
    assert compare(result([[1]], ['foo']), result([[1]], ['bar']))['correct']

@pytest.mark.parametrize('path', ['/health', '/challenges', '/challenges/first-select', '/schema'])
def test_endpoints(client, path):
    assert client.get(path).status_code == 200

def test_solutions_not_leaked(client):
    assert 'solution' not in client.get('/challenges/first-select').json()
    assert 'solution' not in client.get('/challenges').text
    assert client.get('/challenges/first-select/solution?attempts=2').status_code == 422
    assert 'solution' in client.get('/challenges/first-select/solution?attempts=3').json()

def test_submit(client):
    assert client.post('/run', json={'query':'SELECT 1'}).json()['rows'] == [[1]]
    path = '/challenges/first-select/submit'
    assert client.post(path, json={'query':'SELECT id,name,city FROM customers'}).json()['correct']
    assert not client.post(path, json={'query':'SELECT 1'}).json()['correct']
    assert client.post('/run', json={'query':'PRAGMA user_version'}).status_code == 400

@pytest.mark.parametrize('body', [{}, {'query':3}, {'query':True}, {'query':'SELECT 1','extra':1}, {'query':''}, {'query':'x'*8001}])
def test_validation(client, body):
    response = client.post('/run', json=body)
    assert response.status_code == 422
    assert 'input' not in response.text

def test_body_limit(client):
    assert client.post('/run', content='x'*17000).status_code == 413

def test_not_found(client):
    assert client.get('/challenges/missing').status_code == 404

def test_cors(client):
    r = client.options('/run', headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'})
    assert r.headers['access-control-allow-origin'] == 'http://localhost:5173'
    r = client.options('/run', headers={'Origin':'https://evil.example','Access-Control-Request-Method':'POST'})
    assert 'access-control-allow-origin' not in r.headers

def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(main, 'limiter', RateLimiter(1, 100000))
    assert client.post('/run', json={'query':'SELECT 1'}).status_code == 200
    assert client.post('/run', json={'query':'SELECT 1'}).status_code == 429

def test_friendly_error(client):
    r = client.post('/run', json={'query':'SELECT secret_column FROM customers'})
    assert r.status_code == 400
    assert 'schema' in r.json()['detail'] and 'secret_column' not in r.text
