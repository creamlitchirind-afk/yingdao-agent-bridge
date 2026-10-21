"""Build into an empty, allowed flow. Journal checkpoints permit safe fill resumption."""
import hashlib
import json
from pathlib import Path
import settings
import studio_bridge as bridge

def preflight(plan):
    if not isinstance(plan, dict) or not plan.get('flow_id') or not isinstance(plan.get('blocks'), list) or not plan['blocks']:
        raise ValueError('Plan needs flow_id and a nonempty blocks list')
    definitions = settings.definitions()
    for block in plan['blocks']:
        proto = block['prototype']
        if proto not in definitions:
            raise ValueError('Unknown prototype: ' + proto)
        fields = {v['name'] for v in definitions[proto].get('inputs', [])}
        unknown = set(block.get('inputs', {})) - fields
        if unknown:
            raise ValueError('Unknown fields for %s: %s' % (proto, sorted(unknown)))
        if 'output' in block and 'outputs' in block:
            raise ValueError('Use output or outputs, not both')
    for p in plan.get('out_parameters', []):
        if not p.get('name') or not p.get('type') or set(p) - {'name','type','value','description'}:
            raise ValueError('Invalid output parameter')
    return {'valid':True, 'block_count':len(plan['blocks']), 'note':'Field/prototype check only; dynamic parameter semantics are checked by Studio.'}

def build_plan(plan, resume=None):
    preflight(plan)
    flow = plan['flow_id']
    bridge.guard(flow)
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    path = Path(resume).resolve() if resume else settings.state_dir() / 'builds' / (bridge.stamp() + '.json')
    if resume:
        state = json.loads(path.read_text(encoding='utf-8'))
        binding = settings.load()['binding']
        if state['plan_hash'] != digest or state['app_id'] != binding['app_id'] or state['account_fingerprint'] != binding['account_fingerprint']:
            raise ValueError('Resume plan/account/app mismatch')
        if state['stage'] == 'insert_uncertain':
            raise RuntimeError('Insertion outcome uncertain. Inspect flow and evidence; do not replay this build automatically.')
        actual = [b['block_id'] for b in bridge.inspect_flow(flow)['blocks']]
        if actual != [b['block_id'] for b in state['inserted']]:
            raise RuntimeError('Flow changed outside this build; inspect instead of resuming')
        if state['stage'] == 'complete':
            return {'flow_id':flow, 'built':state['inserted'], 'journal':str(path), 'already_complete':True}
    else:
        if bridge.inspect_flow(flow)['total']:
            raise ValueError('Builder requires empty flow; inspect or resume existing journal')
        binding = settings.load()['binding']
        state = {'plan_hash':digest, 'flow_id':flow, 'app_id':binding['app_id'],
                 'account_fingerprint':binding['account_fingerprint'], 'inserted':[], 'filled':0, 'stage':'ready'}
        bridge.dump(path, state)
    try:
        for index, block in enumerate(plan['blocks']):
            if index < state['filled']:
                continue
            if index >= len(state['inserted']):
                state['stage'] = 'insert_uncertain'; bridge.dump(path, state)
                data = bridge.checked(bridge.invoke('flow.edit_blocks', {'flow_id':flow, 'op':'insert',
                    'block_index':-1, 'blocks':[{'prototype_name':block['prototype'], 'comment':block.get('label',block['prototype'])}]}, True))
                inserted = data.get('block_region', {}).get('inserted', [])
                if len(inserted) != 1:
                    raise RuntimeError('Expected one inserted block; inspect result')
                form = inserted[0]
                state['inserted'].append({'block_id':form['block_id'], 'prototype':block['prototype'], 'slots':list(form.get('outputs',{}))})
                state['stage'] = 'fill_pending'; bridge.dump(path, state)
            item = state['inserted'][index]
            fill = {'block_id':item['block_id'], 'inputs':block.get('inputs',{})}
            if 'output' in block:
                if len(item['slots']) != 1:
                    raise ValueError('output shorthand requires exactly one real output slot')
                fill['outputs'] = {item['slots'][0]:block['output']}
            elif 'outputs' in block:
                fill['outputs'] = block['outputs']
            if fill['inputs'] or fill.get('outputs'):
                bridge.checked(bridge.invoke('flow.fill_blocks', {'flow_id':flow, 'fills':[fill]}, True))
            state['filled'] = index + 1
            state['stage'] = 'ready'; bridge.dump(path,state)
        state['stage'] = 'finalize'; bridge.dump(path,state)
        if plan.get('out_parameters'):
            bridge.checked(bridge.invoke('flow.write_parameters', {'flow_id':flow,
                'operations':[dict(op='upsert',direction='Out',**p) for p in plan['out_parameters']]}, True))
        bridge.checked(bridge.invoke('app.save',{},True))
        state['stage'] = 'complete'; state.pop('error',None); bridge.dump(path,state)
        return {'flow_id':flow, 'built':state['inserted'], 'journal':str(path), 'note':'Saved, not executed or business-verified.'}
    except Exception as exc:
        state['error'] = str(exc); bridge.dump(path,state)
        raise RuntimeError(str(exc) + '; build journal: ' + str(path)) from exc
