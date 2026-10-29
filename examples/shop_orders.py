"""Build and run native Yingdao shop flows; verify actual Excel against page evidence."""
from pathlib import Path
import sys,os,json,time,subprocess,math,hashlib,ast,http.client,urllib.parse,uuid
from decimal import Decimal
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import settings,studio_bridge as bridge
from builder import build_plan
from shop_orders_plan import make_plan,remap_variables,URL,HEADERS
TARGET_APP=None  # Loaded from the example's private binding, never from a developer account.
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def configure(allow_unbound=False):
    global TARGET_APP
    original=settings.load();p=Path(os.environ.get('YINGDAO_SHOP_CONFIG',ROOT/'.local/shop-demo/config.json')).resolve();os.environ['YINGDAO_BRIDGE_CONFIG']=str(p)
    if not p.exists():settings.save({k:v for k,v in original.items() if k in ('cli_path','catalog_dir')})
    TARGET_APP=settings.load().get('binding',{}).get('app_id')
    if not TARGET_APP and not allow_unbound:raise RuntimeError('Run shop_orders.py setup --app-id <your current saved Studio app ID> first')
    # Retry only idempotent CLI reads. Never replay an uncertain MCP mutation.
    original_cli=bridge.cli
    def reliable_cli(*args):
        for attempt in range(3):
            try:return original_cli(*args)
            except RuntimeError as exc:
                if 'CLI returned non-JSON' not in str(exc) or args not in {('studio','app','get'),('auth','current')} or attempt==2:raise
                time.sleep(1)
    bridge.cli=reliable_cli
    # Reuse one loopback HTTP connection, without replaying mutation requests.
    endpoint=urllib.parse.urlsplit(bridge.endpoint());connection=http.client.HTTPConnection(endpoint.hostname,endpoint.port,timeout=120)
    def rpc(method,params):
        connection.request('POST',endpoint.path,json.dumps({'jsonrpc':'2.0','id':uuid.uuid4().hex,'method':method,'params':params}).encode(),{'Content-Type':'application/json','Accept':'application/json, text/event-stream'})
        response=connection.getresponse();data=json.loads(response.read())
        if 'error' in data:raise RuntimeError(data['error'])
        return data['result']
    bridge.rpc=rpc
    schemas={x['name']:x['inputSchema'] for x in rpc('tools/list',{})['tools']};bridge.tool_schema=lambda name:schemas[name]

def setup(app_id):
    global TARGET_APP
    configure(allow_unbound=True)
    result=bridge.bind(app_id);TARGET_APP=app_id
    return {'status':'configured','app_id':app_id,'config':str(settings.config_path()),'binding':result}
def normalize(x):
    if isinstance(x,dict):
        if set(x)=={'expression'}:
            try:return ast.literal_eval(x['expression'])
            except (ValueError,SyntaxError):return x
        return {k:normalize(v) for k,v in x.items()}
    if isinstance(x,list):return [normalize(v) for v in x]
    return x
def compare(plan,actual):
    errors=[]
    if len(plan['blocks'])!=len(actual['blocks']):return ['block count differs']
    for i,(wanted,got) in enumerate(zip(plan['blocks'],actual['blocks'])):
        if wanted['prototype']!=got['prototype_name']:errors.append(f'{i}: prototype')
        for k,v in wanted.get('inputs',{}).items():
            expected=normalize(v);observed=normalize(got.get('fields',{}).get(k,{}).get('value'))
            if expected=='' and k in ('replace_text','dest_text') and got.get('fields',{}).get(k)=={}:observed=''
            if type(expected) in (int,float) and isinstance(observed,str):
                try:observed=float(observed)
                except ValueError:pass
            if expected!=observed:errors.append(f'{i}: {k}')
        if wanted.get('output') and wanted['output'] not in got.get('outputs',{}).values():errors.append(f'{i}: output')
        for k,v in wanted.get('outputs',{}).items():
            if got.get('outputs',{}).get(k)!=v:errors.append(f'{i}: output {k}')
    return errors
def verify(record):
    from openpyxl import load_workbook
    pages=json.loads(Path(record['raw_output']).read_text(encoding='utf-8-sig'))
    if not isinstance(pages,list) or not pages or (record['pages'] and len(pages)!=record['pages']):raise ValueError('Incorrect page count')
    if record['pages']==0:
        proof_path=Path(record['raw_output']).with_name(Path(record['raw_output']).stem+'_分页核验.json')
        if not proof_path.exists():raise ValueError('Missing last-page completion proof')
        proof=json.loads(proof_path.read_text(encoding='utf-8-sig'))
        if len(proof)!=3 or proof[0] is not True or 'ant-pagination-disabled' not in proof[1] or proof[2]!=len(pages):raise ValueError('Missing last-page completion proof')
    expected=[];seen=set();first_ids=[]
    for page in pages:
        if not page:raise ValueError('An expected page was empty')
        first_ids.append(page[0][0])
        for row in page:
            if len(row)!=5 or row[1]!=record['product']:raise ValueError('Wrong page product/schema')
            if row[4]=='完成' and row[0] not in seen:
                amount=Decimal(row[2].replace('¥','').replace('￥','').replace(',','').strip())
                if not amount.is_finite():raise ValueError('Non-finite amount')
                expected.append([row[0],row[1],float(amount),row[3],row[4]]);seen.add(row[0])
    if len(first_ids)!=len(set(first_ids)):raise ValueError('Pagination repeated a page')
    wb=load_workbook(record['output'],data_only=False)
    try:
        actual=[list(r) for r in wb.active.values]
        while actual and all(x is None for x in actual[-1]):actual.pop()
        # WPS stores a recognized date as an Excel datetime; compare the same timestamp.
        for row in actual[1:]:
            if len(row)==5 and isinstance(row[3],datetime):
                if row[3].microsecond or row[3].tzinfo is not None:raise ValueError('Unexpected date precision/timezone')
                row[3]=row[3].strftime('%Y-%m-%d %H:%M:%S')
        if actual!=[HEADERS]+expected:raise ValueError('Actual Excel differs from captured pages/order')
        if any(not isinstance(r[2],(int,float)) or isinstance(r[2],bool) for r in actual[1:]):raise ValueError('Amounts are not numeric')
    finally:wb.close()
    total=sum((Decimal(str(x[2])) for x in expected),Decimal(0))
    return {'page_count':len(pages),'source_rows':sum(map(len,pages)),'record_count':len(expected),'total_amount':float(total),'rows':expected,'raw_sha256':digest(record['raw_output']),'output_sha256':digest(record['output']),'exact_rows_and_order':True}
def prepare(product,pages,session):
    session=Path(session).resolve();path=session/'session.json'
    if not product or len(product)>50 or type(pages) is not int or not 0<=pages<=1000:raise ValueError('Provide a product name and all/0 or a positive page count up to 1000')
    if path.exists():
        r=json.loads(path.read_text(encoding='utf-8'))
        if (r['product'],r['pages'])!=(product,pages):raise ValueError('Session parameters differ; do not reuse directory')
        return r
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:4]
    safe_name=''.join('_' if c in '<>:"/\\|?*' or ord(c)<32 else c for c in product).strip(' .') or '商品'
    session.mkdir(parents=True,exist_ok=True);output=session/(safe_name+'_已完成订单_'+stamp+'.xlsx');raw=session/'实际网页采集.json'
    if output.exists() or raw.exists():raise ValueError('Session contains pre-existing results')
    r={'status':'prepared','url':URL,'product':product,'pages':pages,'output':str(output),'raw_output':str(raw),'target_app':TARGET_APP}
    bridge.dump(path,r);bridge.dump(session/'plan.json',make_plan(product,pages,output,raw));return r

def build_from_verified_template(r,session,template):
    """Copy a verified native structure; fill this task's real parameters and reread."""
    source_plan=template['plan'];source_flow=template['flow_id']
    if template['app_id']!=TARGET_APP:raise ValueError('Template app mismatch')
    if compare(source_plan,bridge.inspect_flow(source_flow)):raise ValueError('Verified template changed; revalidate before reuse')
    if not r.get('flow_id'):
        r['status']='create_requested';bridge.dump(session/'session.json',r)
        copied=bridge.checked(bridge.invoke('app.copy_flow',{'flow_id':source_flow,'new_name':'商城订单报表_'+session.name},True))
        bridge.dump(session/'copy_response.json',copied)
        new_id=copied.get('flow_id')
        if not new_id or new_id==source_flow:raise RuntimeError('No unambiguous new flow id; inspect copy response, do not recreate')
        bridge.remember_flow(new_id);r.update(flow_id=new_id,status='building',build_strategy='copy_verified_recipe');bridge.dump(session/'session.json',r)
    plan=remap_variables(make_plan(r['product'],r['pages'],Path(r['output']),Path(r['raw_output'])),template.get('variable_map',{}));plan['flow_id']=r['flow_id'];bridge.dump(session/'plan.json',plan)
    actual=bridge.inspect_flow(r['flow_id'])
    if len(actual['blocks'])!=len(plan['blocks']):raise ValueError('Copied structure differs')
    fills=[]
    for old,wanted,block in zip(source_plan['blocks'],plan['blocks'],actual['blocks']):
        if wanted['prototype']!=block['prototype_name']:raise ValueError('Copied prototype differs')
        changed={k:value for k,value in wanted['inputs'].items() if value!=old['inputs'].get(k)}
        if changed:fills.append({'block_id':block['block_id'],'inputs':changed})
    if fills:r['parameter_fill']=bridge.checked(bridge.invoke('flow.fill_blocks',{'flow_id':r['flow_id'],'fills':fills},True))
    bridge.checked(bridge.invoke('app.save',{},True));actual=bridge.inspect_flow(r['flow_id']);bridge.dump(session/'readback.json',actual);errors=compare(plan,actual);bridge.dump(session/'differences.json',errors)
    if errors:raise ValueError('Copied task readback differs: '+repr(errors))
    r['build']={'strategy':'copy_verified_recipe','template_flow_id':source_flow,'block_count':len(plan['blocks']),'parameter_blocks_changed':len(fills)}
    return r
def execute(product,pages,session):
    session=Path(session).resolve();configure();r=prepare(product,pages,session)
    if r.get('target_app') not in (None,TARGET_APP):raise RuntimeError('Session belongs to a different Studio app; preserve it and use a new session after setup')
    r['target_app']=TARGET_APP;bridge.dump(session/'session.json',r)
    current=bridge.cli_current()['data']
    if current['app']['app_id']!=TARGET_APP:raise RuntimeError('Open and save the Studio app explicitly bound by shop_orders.py setup; current app differs')
    if r.get('run_id'):
        result=bridge.checked(bridge.invoke('app.run_result',{'run_id':r['run_id']}));r['run']=result
    else:
        if r['status'] in ('create_requested','run_requested'):raise RuntimeError('Prior mutation uncertain; inspect evidence before continuing')
        template_path=settings.config_path().parent/'verified_template.json'
        template=json.loads(template_path.read_text(encoding='utf-8')) if template_path.exists() else None
        if template and template.get('app_id')!=TARGET_APP:template=None
        if template and (not r.get('flow_id') or r.get('build_strategy')=='copy_verified_recipe'):
            if current['app']['has_unsaved_changes'] and not r.get('flow_id'):raise RuntimeError('请先保存当前影刀编辑')
            r=build_from_verified_template(r,session,template)
        elif not r.get('flow_id'):
            if current['app']['has_unsaved_changes']:raise RuntimeError('请先保存当前影刀编辑')
            bridge.bind(TARGET_APP);r['status']='create_requested';bridge.dump(session/'session.json',r)
            created=bridge.create_flow('商城订单报表_'+session.name);r.update(flow_id=created['flow_id'],status='building');bridge.dump(session/'session.json',r)
        plan=json.loads((session/'plan.json').read_text(encoding='utf-8'));plan['flow_id']=r['flow_id'];bridge.dump(session/'plan.json',plan)
        if r.get('build_strategy')!='copy_verified_recipe':
            candidates=[]
            for p in settings.state_dir().joinpath('builds').glob('*.json'):
                if json.loads(p.read_text(encoding='utf-8')).get('flow_id')==r['flow_id']:candidates.append(p)
            if len(candidates)>1:raise RuntimeError('Ambiguous build journals')
            r['build']=build_plan(plan,resume=candidates[0] if candidates else None)
        actual=bridge.inspect_flow(r['flow_id']);bridge.dump(session/'readback.json',actual);errors=compare(plan,actual);bridge.dump(session/'differences.json',errors)
        if errors:raise ValueError('Readback mismatch: '+repr(errors))
        r['status']='built';bridge.dump(session/'session.json',r)
        if Path(r['output']).exists() or Path(r['raw_output']).exists():raise ValueError('Output predates this run')
        bridge.validate('app.run',{'flow_id':r['flow_id'],'wait_timeout':45})
        r['status']='run_requested';bridge.dump(session/'session.json',r)
        result=bridge.run_flow(r['flow_id'],45);r.update(run=result,run_id=result.get('run_id'));bridge.dump(session/'session.json',r)
        for attempt in range(3):
            if not result.get('active'):break
            result=bridge.checked(bridge.invoke('app.wait_run_finish',{'run_id':r['run_id'],'timeout':45}));r['run']=result;bridge.dump(session/'session.json',r)
    if result.get('run_succeeded'):
        r['verification']=verify(r);r['status']='verified'
        plan=json.loads((session/'plan.json').read_text(encoding='utf-8'))
        template_path=settings.config_path().parent/'verified_template.json'
        old=json.loads(template_path.read_text(encoding='utf-8')) if template_path.exists() else {}
        variable_map=old.get('variable_map',{}) if r.get('build_strategy')=='copy_verified_recipe' else {}
        bridge.dump(template_path,{'app_id':TARGET_APP,'flow_id':r['flow_id'],'run_id':r['run_id'],'session':str(session),'plan':plan,'variable_map':variable_map})
    elif result.get('active'):r['status']='pending'
    else:r['status']='failed';r['error']=result.get('verification')
    bridge.dump(session/'session.json',r);return r
def gate():
    import msvcrt
    path=ROOT/'.local/shop-demo/worker.lock';path.parent.mkdir(parents=True,exist_ok=True);f=path.open('a+b');f.seek(0);f.write(b'0');f.flush();f.seek(0)
    try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:f.close();return None
    return f
def background(action,product,pages,session,wait=0):
    session=Path(session).resolve();meta=session/'worker.json';record=session/'session.json'
    if action=='status':
        if wait:time.sleep(min(max(wait,0),10))
        r=json.loads(record.read_text(encoding='utf-8')) if record.exists() else {};worker=json.loads(meta.read_text(encoding='utf-8')) if meta.exists() else {}
        result={k:r.get(k) for k in ('status','flow_id','run_id','output','error')}|{'worker':worker}
        if 'verification' in r:result['verification']={k:v for k,v in r['verification'].items() if k!='rows'}
        return result
    prepare(product,pages,session)
    if action=='launch':
        existing=json.loads(record.read_text(encoding='utf-8'));prior=json.loads(meta.read_text(encoding='utf-8')) if meta.exists() else {}
        if existing.get('status')=='verified':return {'status':'verified','next':'query status; task already completed'}
        if prior.get('state')=='failed' or existing.get('status') in ('create_requested','run_requested','failed','pending'):
            return {'status':'blocked','error':prior.get('error') or existing.get('error') or 'Prior task needs evidence review; do not reset or rerun','next':'preserve session and inspect failure'}
        f=gate()
        if f is None:return {'status':'busy','next':'query status only'}
        f.close();previous=json.loads(meta.read_text(encoding='utf-8')) if meta.exists() else {}
        if previous.get('state')=='starting' and time.time()-previous.get('time',0)<30:return {'status':'starting'}
        bridge.dump(meta,{'state':'starting','time':time.time()})
        with (session/'worker.log').open('ab') as log:
            p=subprocess.Popen([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'worker','--product',product,'--pages',str(pages),'--session',str(session)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW)
        return {'status':'started','pid':p.pid,'session':str(session)}
    f=gate()
    if f is None:return {'status':'busy'}
    try:
        bridge.dump(meta,{'state':'running','pid':os.getpid(),'time':time.time()});result=execute(product,pages,session)
        bridge.dump(meta,{'state':'finished','status':result['status'],'time':time.time()});return result
    except Exception as exc:bridge.dump(meta,{'state':'failed','error':str(exc),'time':time.time()});raise
    finally:f.close()
if __name__=='__main__':
    import argparse
    def page_count(value):
        if value.lower() in ('all','全部'):return 0
        return int(value)
    p=argparse.ArgumentParser();p.add_argument('action',choices=['setup','launch','status','worker']);p.add_argument('--app-id');p.add_argument('--product');p.add_argument('--pages',type=page_count,default=0);p.add_argument('--session',type=Path);p.add_argument('--wait',type=int,choices=range(11),default=0);a=p.parse_args()
    if a.action=='setup':
        if not a.app_id:p.error('--app-id is required for setup')
        try:print(json.dumps(setup(a.app_id),ensure_ascii=False,indent=2))
        except Exception as exc:print(json.dumps({'status':'incomplete','error':str(exc)},ensure_ascii=False));sys.exit(1)
        sys.exit(0)
    if a.session is None:p.error('--session is required for launch/status/worker')
    if a.action!='status' and not a.product:p.error('--product is required for launch/worker')
    try:print(json.dumps(background(a.action,a.product,a.pages,a.session,a.wait),ensure_ascii=False,indent=2))
    except Exception as exc:print(json.dumps({'status':'incomplete','error':str(exc)},ensure_ascii=False));sys.exit(1)
