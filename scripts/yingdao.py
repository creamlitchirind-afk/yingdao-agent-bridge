"""Command interface. JSON envelope on stdout, nonzero exit on failure."""
import argparse
import json
from pathlib import Path
import sys
import settings
import studio_bridge as bridge
from builder import build_plan, preflight

def read_json(value):
    return json.loads(Path(value[1:] if value.startswith('@') else value).read_text(encoding='utf-8-sig'))

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['doctor','configure','current','apps','bind','allow-flow','tools',
        'call','create-flow','copy-flow','inspect','preflight','build','run','wait','result','block-docs'])
    parser.add_argument('--app-id'); parser.add_argument('--flow-id'); parser.add_argument('--run-id')
    parser.add_argument('--name'); parser.add_argument('--tool'); parser.add_argument('--args', default='{}')
    parser.add_argument('--plan'); parser.add_argument('--resume'); parser.add_argument('--names')
    parser.add_argument('--cli-path'); parser.add_argument('--catalog-dir')
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--wait', type=int, default=20)
    parser.add_argument('--page',type=int,default=1); parser.add_argument('--search',default='')
    a = parser.parse_args(argv)
    def required(*keys):
        for key in keys:
            if not getattr(a,key):
                raise ValueError('--' + key.replace('_','-') + ' required')
    if a.command in {'allow-flow','call','create-flow','copy-flow','build','run'} and a.command != 'call' and not a.write:
        raise ValueError('--write required')
    if a.command == 'configure':
        config = settings.load()
        if a.cli_path: config['cli_path'] = str(Path(a.cli_path).resolve(strict=True))
        if a.catalog_dir: config['catalog_dir'] = str(Path(a.catalog_dir).resolve(strict=True))
        settings.save(config)
        return {'config':str(settings.config_path())}
    if a.command == 'doctor': return bridge.doctor()
    if a.command == 'current': return bridge.cli_current()['data']
    if a.command == 'apps': return bridge.cli('console','app','--app-type','developed','--page',str(a.page),'--page-size','50','--search',a.search)['data']
    if a.command == 'bind':
        required('app_id'); return bridge.bind(a.app_id)
    if a.command == 'allow-flow':
        required('flow_id'); return bridge.allow_flow(a.flow_id)
    if a.command == 'tools':
        data = bridge.rpc('tools/list',{})
        if a.names: data['tools'] = [t for t in data['tools'] if t['name'] in a.names.split(',')]
        return data
    if a.command == 'block-docs':
        required('names'); docs = settings.definitions(); names = a.names.split(',')
        return {'documents':{n:docs[n] for n in names if n in docs}, 'missing':[n for n in names if n not in docs]}
    if a.command == 'call':
        required('tool')
        args = read_json(a.args) if a.args.startswith('@') else json.loads(a.args)
        return bridge.checked(bridge.invoke(a.tool,args,a.write))
    if a.command == 'create-flow':
        required('name'); return bridge.create_flow(a.name)
    if a.command == 'copy-flow':
        required('flow_id'); args = {'flow_id':a.flow_id}
        if a.name: args['new_name'] = a.name
        result = bridge.checked(bridge.invoke('app.copy_flow',args,True))
        # Result schema can vary: only enable an unambiguously returned new flow ID.
        flow = result.get('flow_id')
        if flow and flow != a.flow_id: bridge.remember_flow(flow)
        return result
    if a.command == 'inspect':
        required('flow_id'); return bridge.inspect_flow(a.flow_id)
    if a.command in {'preflight','build'}:
        required('plan'); plan=read_json(a.plan)
        if a.flow_id: plan['flow_id']=a.flow_id
        return preflight(plan) if a.command=='preflight' else build_plan(plan,a.resume)
    if a.command == 'run':
        required('flow_id'); return bridge.run_flow(a.flow_id,a.wait)
    if a.command in {'wait','result'}:
        required('run_id'); bridge.guard()
        args={'run_id':a.run_id}
        if a.command=='wait': args['timeout']=a.wait
        return bridge.checked(bridge.invoke('app.wait_run_finish' if a.command=='wait' else 'app.run_result',args))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        data=main()
        ok = data.get('ready',True) is not False and data.get('run_succeeded') is not False
        print(json.dumps({'ok':ok,'data':data},ensure_ascii=False,indent=2))
        sys.exit(0 if ok else 1)
    except Exception as exc:
        print(json.dumps({'ok':False,'error':{'type':type(exc).__name__,'message':str(exc)}},ensure_ascii=False,indent=2))
        sys.exit(1)
