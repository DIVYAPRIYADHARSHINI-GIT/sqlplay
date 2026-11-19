"""Explicit live verification; not collected by pytest. No tokens or query logging."""
import json
from pathlib import Path
import sys
import time
import urllib.request
import urllib.error

api_url, origin, output = sys.argv[1:4]
catalog = json.loads((Path(__file__).parents[1] / 'data/challenges.json').read_text())
checks = []

def request(path, method='GET', body=None, headers=None):
    req = urllib.request.Request(api_url.rstrip('/') + path, data=json.dumps(body).encode() if body is not None else None, method=method, headers={'Content-Type': 'application/json', **(headers or {})})
    start = time.perf_counter()
    try:
        response = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        response = e
    raw = response.read().decode()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = raw[:300]
    return response.status, data, dict(response.headers), round((time.perf_counter()-start)*1000,2)

def check(name, condition, detail=None):
    checks.append({'name':name,'passed':bool(condition),'detail':detail})
    print(('PASS ' if condition else 'FAIL ') + name)
    Path(output).write_text(json.dumps({'api':api_url,'origin':origin,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'checks':checks,'complete':False},indent=2))

for i in range(3):
    code,data,headers,ms = request('/health')
    check(f'health request {i+1}', code==200 and data.get('status')=='ok' and data.get('challenges')==44, {'elapsed_ms':ms,'response':data})
code,data,_,_ = request('/challenges')
check('catalog: 44 public summaries, no solutions',code==200 and len(data)==44 and all('solution' not in c for c in data))
code,data,_,_ = request('/schema')
check('schema: seven connected tables',code==200 and len(data['tables'])==7)
for c in catalog:
    code,data,_,ms = request(f"/challenges/{c['id']}/submit",'POST',{'query':c['solution']})
    check(f"reference passes: {c['id']}",code==200 and data.get('correct') is True,{'elapsed_ms':ms})
    code,data,_,_ = request(f"/challenges/{c['id']}/submit",'POST',{'query':'SELECT NULL WHERE 0'})
    check(f"wrong answer fails: {c['id']}",code==200 and data.get('correct') is False)
for name,query in [('multiple statements','SELECT 1; SELECT 2'),('write','DELETE FROM customers'),('pragma','PRAGMA user_version'),('attach',"ATTACH DATABASE '/tmp/x' AS x"),('extension',"SELECT load_extension('x')"),('slow recursion','WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n) SELECT SUM(x) FROM n'),('row limit','SELECT a.id FROM order_items a CROSS JOIN order_items b')]:
    code,data,_,ms=request('/run','POST',{'query':query})
    check('safety: '+name,code==400,{'message':data.get('detail') if isinstance(data,dict) else data,'elapsed_ms':ms})
code,data,headers,_=request('/run','OPTIONS',headers={'Origin':origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'})
check('CORS allows exact live frontend',code==200 and next((v for k,v in headers.items() if k.lower()=='access-control-allow-origin'),None)==origin)
code,data,headers,_=request('/run','OPTIONS',headers={'Origin':'https://not-allowed.example','Access-Control-Request-Method':'POST'})
check('CORS rejects unlisted origin',not any(k.lower()=='access-control-allow-origin' for k in headers))
code,data,_,_=request('/run','POST',{'query':123})
check('strict query type validation',code==422)
code,data,_,_=request('/run','POST',{'query':'SELECT COUNT(*) FROM customers'})
check('seed intact after safety tests',code==200 and data['rows']==[[16]])
result={'api':api_url,'origin':origin,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'checks':checks,'note':'HTTP duration includes network. These are repeated requests; infrastructure cold starts cannot be forced or conclusively identified by this script.'}
Path(output).write_text(json.dumps(result,indent=2))
print(json.dumps({k:result[k] for k in ('passed','failed')}))
sys.exit(1 if result['failed'] else 0)
