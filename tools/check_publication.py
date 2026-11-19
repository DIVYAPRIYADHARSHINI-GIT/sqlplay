"""Audit the Git index and reachable text history without printing matched values.

This is a conservative pattern check, not a guarantee of complete secret detection.
It never reads authentication stores or ignored working-tree environment files.
"""
import json
from pathlib import PurePosixPath
import re
import subprocess
import sys


def git(*args):
    return subprocess.check_output(['git', *args])


patterns = {
    'GitHub credential': rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
    'Private key': rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    'AWS access key': rb'(?:AKIA|ASIA)[A-Z0-9]{16}',
    'Stripe secret': rb'sk_live_[A-Za-z0-9]{20,}',
    'Assigned credential': rb'(?i)(?:VERCEL_TOKEN|GITHUB_TOKEN|GH_TOKEN|API_SECRET|PASSWORD)\s*[=:]\s*[\x22\x27]?[A-Za-z0-9_./+=-]{20,}',
}
paths = git('ls-files', '-z').decode().split('\0')[:-1]
dotenv = [p for p in paths if PurePosixPath(p).name.startswith('.env') or re.search(r'\.env(?:\.|$)', PurePosixPath(p).name)]
objects = {}
for p in paths:
    if PurePosixPath(p).suffix.lower() not in {'.png', '.pdf', '.jpg', '.jpeg', '.woff', '.woff2'}:
        objects[git('rev-parse', ':' + p).strip().decode()] = p
for line in git('rev-list', '--objects', '--all').decode().splitlines():
    fields = line.split(' ', 1)
    if len(fields) == 2 and PurePosixPath(fields[1]).suffix.lower() not in {'.png', '.pdf', '.jpg', '.jpeg', '.woff', '.woff2'}:
        objects.setdefault(fields[0], fields[1])
findings = []
scanned = 0
for oid, name in objects.items():
    if git('cat-file', '-t', oid).strip() != b'blob':
        continue
    content = git('cat-file', 'blob', oid)
    if b'\0' in content:
        continue
    scanned += 1
    for label, pattern in patterns.items():
        if re.search(pattern, content):
            findings.append({'file': name, 'pattern': label})  # Never echo a value.
result = {'tracked_files': len(paths), 'text_blobs_checked_in_index_and_history': scanned, 'dotenv_files_in_index': dotenv, 'credential_pattern_findings': findings, 'scope': 'Git index and reachable text history; ignored local files and auth stores are not read.'}
print(json.dumps(result, indent=2))
sys.exit(1 if dotenv or findings else 0)
