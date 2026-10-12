"""Human-facing local approval console; never exposed over MCP."""
import difflib
import json
import sys
from engine import Files

files = Files()
pending = [json.loads(p.read_text('utf-8')) for p in files.runtime.glob('*.json')]
pending = [r for r in pending if r.get('status') == 'pending']
if len(sys.argv) == 1:
    for r in pending:
        print(r['id'], r['operation'], r['root'], r['path'])
    print('Review a request with: .\\service\\.venv\\Scripts\\python.exe service/review.py <request_id>')
else:
    r = files.request(sys.argv[1])
    print('Request:', r['id'], '\nOperation:', r['operation'], '\nRoot:', r['root'], '\nPath:', r['path'])
    if r['operation'] == 'write':
        p = files.path(r['root'], r['path'])
        before = p.read_text('utf-8') if p.exists() else ''
        print(''.join(difflib.unified_diff(before.splitlines(True), r['text'].splitlines(True), fromfile='current', tofile='proposed')))
    else:
        print('Destination:', r['destination'])
    print('Treat proposed content as untrusted. Approval changes files on this computer.')
    choice = input('Type APPLY to apply, REJECT to reject, or Enter to leave pending: ')
    if choice == 'APPLY':
        print(files.apply(r['id']))
    elif choice == 'REJECT':
        r['status'] = 'rejected'
        (files.runtime / (r['id'] + '.json')).write_text(json.dumps(r, indent=2), 'utf-8')
        files.audit('reject', r['root'], r['path'], request_id=r['id'])
        print('Rejected')
