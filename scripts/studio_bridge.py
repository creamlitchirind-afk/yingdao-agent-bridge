"""Experimental Windows Studio bridge; all mutations require an account/app binding.

This is an accident-prevention boundary, not a sandbox for untrusted agents or code.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request
import uuid
import settings

READ = {'app.get_info', 'app.list_flows', 'flow.blocks.list', 'flow.list_parameters',
        'app.logs', 'app.run_result', 'app.wait_run_finish', 'diagnostics.snapshot',
        'wiki.list', 'wiki.search', 'wiki.read', 'selector.list', 'selector.details',
        'codeflow.read', 'flow.get_variable_snapshots', 'flow.list_variables',
        'app.global_variables.list'}
WRITE = {'app.rename_flow','app.delete_flow','flow.fill_blocks', 'flow.edit_blocks', 'flow.write_parameters',
         'app.run', 'app.save', 'app.create_flow', 'app.copy_flow', 'codeflow.write'}

def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:8]

def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)

def cli(*args):
    env = dict(os.environ, SWITCH_STUDIO_MCP_CLI_SUPPORT='1')
    p = subprocess.run([str(settings.cli_path()), *args], env=env, capture_output=True,
                       text=True, encoding='utf-8', timeout=40)
    try:
        data = json.loads(p.stdout.lstrip('\ufeff'))
    except ValueError:
        raise RuntimeError('CLI returned non-JSON; inspect CLI help/version locally') from None
    if not data.get('ok'):
        raise RuntimeError(data.get('message') or data.get('error') or 'CLI failed')
    return data

def cli_current():
    return cli('studio', 'app', 'get')

def account_fingerprint():
    data = cli('auth', 'current')['data']
    if not data.get('loggedIn') or not data.get('userId'):
        raise RuntimeError('Log in to Yingdao first')
    identity = str(data['userId']) + ':' + str(data.get('accountTypeCode', ''))
    return hashlib.sha256(identity.encode()).hexdigest()

def endpoint():
    files = list(Path(tempfile.gettempdir()).glob('shadowbot.cli.*.port'))
    if len(files) != 1:
        raise RuntimeError('Expected one ShadowBot session port file, found %d. Resolve stale/multiple sessions first.' % len(files))
    port = int(files[0].read_text(encoding='utf-8-sig').strip())
    if not 1 <= port <= 65535:
        raise ValueError('Invalid local port')
    return 'http://127.0.0.1:%d/api/v1/mcp' % port

def rpc(method, params):
    request_id = uuid.uuid4().hex
    req = urllib.request.Request(endpoint(), json.dumps({'jsonrpc':'2.0', 'id':request_id,
        'method':method, 'params':params}).encode(),
        {'Content-Type':'application/json', 'Accept':'application/json, text/event-stream'})
    # Ignore proxy environment for local IPC; disallow redirecting to non-local services.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(req, timeout=60) as response:
        result = json.load(response)
    if 'error' in result:
        raise RuntimeError(json.dumps(result['error'], ensure_ascii=False))
    return result['result']

def checked(result):
    data = result.get('structuredContent')
    if data is None:
        for item in result.get('content', []):
            if item.get('type') == 'text':
                try:
                    data = json.loads(item['text']); break
                except ValueError:
                    pass
    if not isinstance(data, dict):
        raise RuntimeError('Expected structured tool result')
    if (result.get('isError') or data.get('success') is False or data.get('fill_errors')
            or data.get('failed_count', 0) or data.get('state') in ('rejected', 'rolled_back')):
        raise RuntimeError(json.dumps(data, ensure_ascii=False))
    # Required-field validation errors immediately after insertion are not a failed insertion.
    return data

def guard(flow_id=None):
    binding = settings.load().get('binding', {})
    if not binding or binding.get('account_fingerprint') != account_fingerprint():
        raise RuntimeError('Account is unbound or changed. Open intended app and bind again.')
    current = cli_current()['data']
    if current.get('app', {}).get('app_id') != binding.get('app_id'):
        raise RuntimeError('Current Studio app differs from binding; no mutation sent.')
    if flow_id is not None and flow_id not in binding.get('allowed_flows', []):
        raise RuntimeError('Flow is not enabled for writes/runs. Copy it or explicitly allow-flow first.')
    return current

def bind(app_id):
    current = cli_current()['data']
    if current.get('app', {}).get('app_id') != app_id:
        raise RuntimeError('Requested app is not the currently open Studio app')
    config = settings.load()
    config['binding'] = {'app_id': app_id, 'account_fingerprint': account_fingerprint(), 'allowed_flows': []}
    settings.save(config)
    return {'app_id':app_id, 'allowed_flows':[], 'note':'Binding reset; old-account flow permissions are not reused.'}

def remember_flow(flow_id):
    guard()
    config = settings.load()
    flows = config['binding']['allowed_flows']
    if flow_id not in flows:
        flows.append(flow_id)
    settings.save(config)

def tool_schema(name):
    tools = rpc('tools/list', {}).get('tools', [])
    for tool in tools:
        if tool['name'] == name:
            return tool['inputSchema']
    raise ValueError('Tool unavailable in this Studio version: ' + name)

def validate(name, arguments):
    import jsonschema
    jsonschema.validate(arguments, tool_schema(name))
    if name in {'app.run', 'app.wait_run_finish'}:
        key = 'wait_timeout' if name == 'app.run' else 'timeout'
        if key not in arguments or not 0 <= arguments[key] <= 45:
            raise ValueError('Explicit wait must be between 0 and 45 seconds; continue with same run_id.')

def inspect_flow(flow_id):
    blocks = []; offset = 0
    while True:
        data = checked(invoke('flow.blocks.list', {'flow_id':flow_id, 'detail':'detail', 'offset':offset, 'limit':50}))
        blocks.extend(data['blocks'])
        next_offset = data.get('next_offset')
        if next_offset is None:
            return {'flow_id':flow_id, 'blocks':blocks, 'total':len(blocks)}
        if next_offset <= offset:
            raise RuntimeError('Invalid pagination cursor')
        offset = next_offset

def invoke(name, arguments, allow_write=False):
    if name not in READ | WRITE:
        raise ValueError('Tool outside bridge scope: ' + name)
    mutation = name in WRITE
    if mutation and not allow_write:
        raise ValueError('Explicit --write is required')
    validate(name, arguments)
    if mutation:
        if name in {'app.rename_flow','app.delete_flow'} and arguments.get('force'):
            raise ValueError('Forced flow changes are not supported by this bridge')
        if name=='app.delete_flow':
            for flow_id in arguments['flow_ids']:
                if flow_id=='main':raise ValueError('Cannot delete main')
                guard(flow_id)
        target = arguments.get('flow_id')
        if name not in {'app.create_flow', 'app.save','app.delete_flow'} and not target:
            raise ValueError('Explicit flow_id required')
        guard(None if name == 'app.copy_flow' else target)
    evidence = settings.state_dir() / 'evidence' / (stamp() + '.json')
    record = {'tool':name, 'arguments':arguments, 'status':'prepared'}
    if mutation:
        if name.startswith('flow.'):
            kinds=checked(invoke('app.list_flows',{})).get('flows',[]) if name=='flow.write_parameters' else []
            is_code=any(f['flow_id']==arguments['flow_id'] and f['flow_kind']=='code' for f in kinds)
            record['before'] = checked(invoke('codeflow.read',{'flow_id':arguments['flow_id']})) if is_code else inspect_flow(arguments['flow_id'])
            record['parameters_before'] = rpc('tools/call', {'name':'flow.list_parameters', 'arguments':{'flow_id':arguments['flow_id']}})
        elif name == 'codeflow.write':
            record['before'] = rpc('tools/call', {'name':'codeflow.read', 'arguments':{'flow_id':arguments['flow_id']}})
        elif name in {'app.rename_flow','app.delete_flow'}:
            affected=arguments['flow_ids'] if name=='app.delete_flow' else [arguments['flow_id']]
            record['before']=[inspect_flow(flow_id) for flow_id in affected]
        record['binding'] = {'app_id':settings.load()['binding']['app_id']}
    dump(evidence, record)
    try:
        if mutation:
            guard(None if name == 'app.copy_flow' else arguments.get('flow_id'))
        result = rpc('tools/call', {'name':name, 'arguments':arguments})
        record.update(status='response_received', result=result)
        dump(evidence, record)
        return result
    except Exception as exc:
        record.update(status='uncertain' if mutation else 'failed', error=str(exc))
        dump(evidence, record)
        raise RuntimeError(str(exc) + '; evidence: ' + str(evidence)) from exc

def create_flow(name):
    result = invoke('app.create_flow', {'flows':[{'flow_name':name, 'kind':'visual'}]}, True)
    data = checked(result)
    flow = data['results'][0]['flow_id']
    remember_flow(flow)
    return {'flow_id':flow, 'flow_name':name}

def allow_flow(flow_id):
    guard()
    snapshot = inspect_flow(flow_id)
    path = settings.state_dir() / 'snapshots' / (stamp() + '.json')
    dump(path, snapshot)
    remember_flow(flow_id)
    return {'flow_id':flow_id, 'snapshot':str(path)}

def run_flow(flow_id, wait=20):
    return checked(invoke('app.run', {'flow_id':flow_id, 'wait_timeout':wait}, True))

def doctor():
    checks = {}
    probes = [('cli', lambda: str(settings.cli_path())), ('account', lambda: {'logged_in':bool(account_fingerprint())}),
        ('studio', lambda: cli_current()['data']), ('tools', lambda: {'count':len(rpc('tools/list', {})['tools'])}),
        ('catalog', lambda: str(settings.catalog_dir())), ('binding', lambda: {'app_id':guard()['app']['app_id']})]
    for label, probe in probes:
        try:
            checks[label] = {'ok':True, 'data':probe()}
        except Exception as exc:
            checks[label] = {'ok':False, 'error':str(exc)}
    return {'ready':all(c['ok'] for c in checks.values()), 'checks':checks}
