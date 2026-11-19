"""Memory-only SQLite sandbox. No query logging or filesystem database."""
from collections import Counter
import json
import math
from pathlib import Path
import re
import sqlite3
import threading
import time
import uuid

DATA = Path(__file__).parent / 'data'
CHALLENGES = json.loads((DATA / 'challenges.json').read_text())
BY_ID = {c['id']: c for c in CHALLENGES}
TABLES = {'customers', 'orders', 'order_items', 'products', 'categories', 'employees', 'departments'}
MAX_ROWS = 500
MAX_SQL = 8000
TIME_LIMIT = 0.20
FUNCTIONS = set('abs avg ceil ceiling char coalesce concat concat_ws count cume_dist date datetime dense_rank first_value floor format glob group_concat hex ifnull iif instr julianday lag last_value lead length like lower ltrim max min mod nth_value ntile nullif percent_rank pow power rank replace round row_number rtrim sign strftime substr substring sum time timediff total trim trunc typeof unicode unixepoch upper'.split())


class QueryError(ValueError):
    pass


class Database:
    def __init__(self):
        if sqlite3.sqlite_version_info < (3, 39, 0):
            raise RuntimeError('SQLite 3.39+ is required for RIGHT and FULL JOIN.')
        self.uri = f'file:/sqlplay-{uuid.uuid4().hex}?vfs=memdb'
        self.keeper = sqlite3.connect(self.uri, uri=True, check_same_thread=False)
        self.keeper.executescript((DATA / 'seed.sql').read_text())
        self.keeper.commit()
        self.schema = []
        for table in sorted(TABLES):
            columns = [{'name': r[1], 'type': r[2], 'nullable': not bool(r[3] or r[5]), 'primary_key': bool(r[5])} for r in self.keeper.execute(f'PRAGMA table_info({table})')]
            links = [{'column': r[3], 'table': r[2], 'target': r[4]} for r in self.keeper.execute(f'PRAGMA foreign_key_list({table})')]
            rows = self.keeper.execute(f'SELECT * FROM {table} LIMIT 3').fetchall()
            self.schema.append({'name': table, 'columns': columns, 'foreign_keys': links, 'sample_rows': rows, 'row_count': self.keeper.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]})

    def connect(self):
        # memdb VFS holds the database in RAM; mode=ro is enforced by SQLite itself.
        con = sqlite3.connect(self.uri + '&mode=ro', uri=True, timeout=0.1)
        # Some serverless Python builds compile extension loading out entirely.
        # In that case the method is absent and loading is already impossible.
        if hasattr(con, 'enable_load_extension'):
            con.enable_load_extension(False)
        con.execute('PRAGMA query_only=ON')
        con.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 100_000)
        con.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, MAX_SQL)
        con.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 64)
        con.setlimit(sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 50)
        con.setlimit(sqlite3.SQLITE_LIMIT_COMPOUND_SELECT, 20)
        con.setlimit(sqlite3.SQLITE_LIMIT_VDBE_OP, 25_000)
        con.setlimit(sqlite3.SQLITE_LIMIT_FUNCTION_ARG, 20)
        con.set_authorizer(self.authorize)
        return con

    @staticmethod
    def authorize(action, arg1, arg2, db_name, source):
        if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ and arg1 in TABLES and (db_name == 'main' or (db_name is None and arg2 == '')):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and (arg2 or '').lower() in FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    def run(self, query, time_limit=TIME_LIMIT):
        if not isinstance(query, str) or not query.strip() or len(query) > MAX_SQL:
            raise QueryError(f'Write a query between 1 and {MAX_SQL} characters long.')
        if '\x00' in query:
            raise QueryError('Remove the unsupported null character from your query.')
        # Ignore leading comments only. sqlite3.execute parses statement boundaries,
        # so a semicolon inside a string remains valid, but a second statement cannot run.
        prefix = re.sub(r'\A(?:\s+|--[^\n]*(?:\n|$)|/\*[\s\S]*?\*/)*', '', query)
        if not re.match(r'(?i)(SELECT|WITH)\b', prefix):
            raise QueryError('Only one read-only SELECT or WITH query is allowed. This database cannot be changed.')
        started = time.perf_counter()
        con = self.connect()
        ticks = 0
        def budget():
            nonlocal ticks
            ticks += 1
            return ticks > 20_000 or time.perf_counter() - started > time_limit
        con.set_progress_handler(budget, 1000)
        try:
            cursor = con.execute(query)
            if cursor.description is None:
                raise QueryError('Use SELECT to return a result table.')
            rows = cursor.fetchmany(MAX_ROWS + 1)
            if len(rows) > MAX_ROWS:
                raise QueryError(f'This query returns more than {MAX_ROWS} rows. Add a WHERE condition or LIMIT {MAX_ROWS}.')
            # JSON cannot represent binary or non-finite numeric values safely.
            if any(isinstance(v, bytes) or isinstance(v, float) and not math.isfinite(v) for row in rows for v in row):
                raise QueryError('Return text or finite numbers, not binary data or infinity.')
            return {'columns': [c[0] for c in cursor.description], 'rows': rows, 'row_count': len(rows), 'elapsed_ms': round((time.perf_counter() - started) * 1000, 2)}
        except QueryError:
            raise
        except (sqlite3.Error, MemoryError, OverflowError) as exc:
            message = str(exc).lower()
            if 'one statement' in message:
                friendly = 'Run just one statement at a time. Remove the extra statement after the semicolon.'
            elif 'interrupted' in message:
                friendly = 'This query took too long. Check your joins, reduce recursion or filter the data first.'
            elif 'no such table' in message:
                friendly = 'That table was not found. Check its spelling in the schema explorer.'
            elif 'no such column' in message:
                friendly = 'That column was not found. Check the schema and use a table alias when needed.'
            elif 'ambiguous' in message:
                friendly = 'More than one table has that column. Add its table name or alias.'
            elif 'syntax' in message or 'incomplete' in message:
                friendly = 'SQLite could not read this syntax. Check commas, quotes, parentheses and clause order.'
            elif 'authoriz' in message or 'prohibit' in message or 'readonly' in message:
                friendly = 'That operation is not allowed. Use a read-only query on the sample tables and supported functions.'
            elif 'no such function' in message:
                friendly = 'That function is unavailable in SQLite. Try strftime for dates, or check the dialect notes.'
            else:
                friendly = 'SQLite could not run this query within the safety limits. Simplify the expression and check its data types.'
            raise QueryError(friendly) from None
        finally:
            con.close()


def same_value(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-7, abs_tol=1e-6)
    return type(a) is type(b) and a == b


def compare(actual, expected, ordered=False):
    if len(actual['columns']) != len(expected['columns']):
        return {'correct': False, 'kind': 'columns', 'message': f"Expected {len(expected['columns'])} columns, but your query returned {len(actual['columns'])}. Check the selected columns and their positions."}
    if len(actual['rows']) != len(expected['rows']):
        return {'correct': False, 'kind': 'rows', 'message': f"Expected {len(expected['rows'])} rows, but your query returned {len(actual['rows'])}. Check filters, joins and duplicate rows."}
    def matches(a, b):
        return all(same_value(x, y) for x, y in zip(a, b))
    if ordered:
        for index, (a, b) in enumerate(zip(actual['rows'], expected['rows'])):
            if not matches(a, b):
                return {'correct': False, 'kind': 'values_or_order', 'message': f'Values or order differ at row {index + 1}. Check ORDER BY, tie-breakers and selected column positions.'}
    else:
        # Bipartite matching avoids greedy errors where tolerant numeric matches overlap.
        candidates = [[j for j, b in enumerate(expected['rows']) if matches(a, b)] for a in actual['rows']]
        assigned = {}
        def augment(i, seen):
            for j in candidates[i]:
                if j in seen:
                    continue
                seen.add(j)
                if j not in assigned or augment(assigned[j], seen):
                    assigned[j] = i
                    return True
            return False
        if any(not augment(i, set()) for i in range(len(candidates))):
            return {'correct': False, 'kind': 'values', 'message': 'The row and column counts match, but some values differ. Check calculations, NULL handling, duplicates and column positions.'}
    return {'correct': True, 'kind': 'correct', 'message': 'Nicely done! Every value matches' + (' in the required order.' if ordered else '. Column names and row order do not affect this challenge.')}


class RateLimiter:
    """Per-process, global bucket: stores no IPs, queries or learner identifiers."""
    def __init__(self, capacity=120, period=60):
        self.capacity, self.period = capacity, period
        self.tokens = float(capacity)
        self.updated = time.monotonic()
        self.lock = threading.Lock()

    def allow(self):
        with self.lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.capacity / self.period)
            self.updated = now
            if self.tokens < 1:
                return False
            self.tokens -= 1
            return True
