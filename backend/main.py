import os
import sqlite3
import threading
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from engine import Database, BY_ID, CHALLENGES, MAX_SQL, QueryError, RateLimiter, compare

app = FastAPI(title='SQLPlay API', version='1.0.0', docs_url=None, redoc_url=None)
database = Database()
limiter = RateLimiter()
slots = threading.BoundedSemaphore(4)
origins = [x.strip().rstrip('/') for x in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if x.strip()]
if '*' in origins:
    raise RuntimeError('CORS_ORIGINS must list exact origins, not a wildcard.')

class BodyLimit:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] not in ('POST', 'PUT', 'PATCH'):
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            body.extend(message.get('body', b''))
            if len(body) > 16000:
                return await JSONResponse({'detail': 'This request is too large. Keep queries below 8,000 characters.'}, status_code=413)(scope, receive, send)
            if not message.get('more_body'):
                break
        sent = False
        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()
        await self.app(scope, replay, send)

app.add_middleware(BodyLimit)
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'], allow_credentials=False)

class QueryInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    query: str = Field(min_length=1, max_length=MAX_SQL)

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc):
    # Pydantic's default errors echo submitted input; deliberately do not expose it.
    return JSONResponse({'detail': 'Use a JSON object with only a query string (1–8,000 characters), or check the request parameters.'}, status_code=422)

@app.exception_handler(QueryError)
async def query_error(request: Request, exc):
    return JSONResponse({'detail': str(exc)}, status_code=400)

@app.middleware('http')
async def headers(request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

def challenge(cid):
    if cid not in BY_ID:
        raise HTTPException(404, 'Challenge not found. Choose another from the library.')
    return BY_ID[cid]

def public(c, detail=False):
    keys = ['id', 'title', 'level', 'topic', 'ordered'] + (['statement', 'hints'] if detail else [])
    return {k: c[k] for k in keys}

def execute(query, reference=None, ordered=False):
    if not limiter.allow():
        raise HTTPException(429, 'The practice server is busy. Take a short break and try again.', headers={'Retry-After': '5'})
    if not slots.acquire(blocking=False):
        raise HTTPException(429, 'A few queries are running. Please retry in a moment.', headers={'Retry-After': '2'})
    try:
        result = database.run(query)
        if reference is not None:
            return {**result, **compare(result, database.run(reference), ordered)}
        return result
    finally:
        slots.release()

@app.get('/health')
def health():
    try:
        database.run('SELECT 1')  # Exercise the real restricted execution path.
    except Exception:
        raise HTTPException(503, 'The sample database is not ready. Please retry.') from None
    return {'status': 'ok', 'database': 'SQLite', 'sqlite_version': sqlite3.sqlite_version, 'challenges': len(CHALLENGES), 'storage': 'memory-only'}

@app.get('/challenges')
def list_challenges():
    return [public(c) for c in CHALLENGES]

@app.get('/challenges/{cid}')
def get_challenge(cid: str):
    return public(challenge(cid), True)

@app.get('/challenges/{cid}/solution')
def solution(cid: str, attempts: int = Query(ge=3, le=100000)):
    # Learning affordance, not an authentication boundary: attempts live only in the browser.
    return {'solution': challenge(cid)['solution']}

@app.get('/schema')
def schema():
    return {'dialect': 'SQLite', 'tables': database.schema, 'limits': {'rows': 500, 'query_characters': MAX_SQL, 'execution_seconds': 0.2}}

@app.post('/run')
def run(body: QueryInput):
    return execute(body.query)

@app.post('/challenges/{cid}/submit')
def submit(cid: str, body: QueryInput):
    c = challenge(cid)
    return execute(body.query, c['solution'], c['ordered'])
