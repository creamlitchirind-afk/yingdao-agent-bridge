"""Deterministic native Studio demo. Python prepares plans and verifies, never writes results."""
import argparse, copy, hashlib, json, math, os, sys, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import settings
import studio_bridge as bridge
from builder import build_plan

TARGET_APP = None  # Runtime binding in the private example configuration.
HEADERS = ['学院', '班级', '姓名', '缺勤学时']

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_rows(path, allow_empty=False):
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=False)
    try:
        if len(wb.worksheets) != 1:
            raise ValueError('Demo requires exactly one worksheet')
        rows = list(wb.active.values)
        while rows and all(v is None for v in rows[-1]): rows.pop()
        if not rows or list(rows[0]) != HEADERS:
            raise ValueError('Expected exactly four columns: ' + repr(HEADERS))
        for row in rows[1:]:
            if len(row) != 4 or any(v is None for v in row):
                raise ValueError('Empty or incomplete data row; fix input before demo')
            if any(isinstance(v, str) and v.startswith('=') for v in row):
                raise ValueError('Formula input is outside this demo')
            if not isinstance(row[3], (int,float)) or isinstance(row[3], bool) or not math.isfinite(row[3]):
                raise ValueError('Hours must be a finite number')
        if len(rows) < 2 and not allow_empty: raise ValueError('No input data')
        return [list(r) for r in rows]
    finally:
        wb.close()

def make_plan(source, output, rows):
    steps = json.loads((ROOT/'examples/attendance_video_native_recipe.json').read_text(encoding='utf-8'))
    steps[0]['inputs']['open_filename'] = str(source)
    steps[1]['inputs']['area_end_row_num'] = {'expression': str(len(rows))}
    steps[9]['inputs']['save_filename'] = str(output)
    labels = ['打开考勤原表','读取数据并排除表头','准备结果列表','逐条检查考勤记录','读取该行学时',
              '判断缺勤学时大于零','保留整条记录','结束判断','结束循环','新建结果工作簿',
              '准备四列表头','写入表头','统计符合条件的记录','有异常记录才写入','批量写入筛选结果','结束结果判断','保存并关闭结果']
    return {'flow_id':'PENDING', 'blocks':[dict(prototype=s['prototype_name'], label=label,
                inputs=s['inputs'], outputs=s.get('outputs') or {}) for s,label in zip(steps,labels)]}

def compare_plan(plan, actual):
    errors=[]
    blocks=actual['blocks']
    if len(blocks)!=len(plan['blocks']): return ['block count mismatch']
    for i,(expected,block) in enumerate(zip(plan['blocks'],blocks),1):
        if block.get('prototype_name')!=expected['prototype']: errors.append(f'{i}: prototype')
        for key,value in expected['inputs'].items():
            field=block.get('fields',{}).get(key,{})
            if 'value' not in field or type(field['value']) is not type(value) or field['value']!=value:
                errors.append(f'{i}: {key}: expected {value!r}, got {field.get("value")!r}')
        if (block.get('outputs') or {})!=expected['outputs']: errors.append(f'{i}: outputs')
    return errors

def verify_output(record):
    rows=read_rows(record['output'],allow_empty=True)
    expected=[HEADERS]+record['expected']
    if rows!=expected: raise ValueError('Output records/order differ from expected: '+repr(rows))
    if digest(record['source'])!=record['input_sha256']: raise ValueError('Input changed')
    return {'rows':rows[1:], 'record_count':len(rows)-1,
            'total_hours':sum(float(r[3]) for r in rows[1:]), 'input_unchanged':True,
            'output_sha256':digest(record['output'])}

def configure(allow_unbound=False):
    global TARGET_APP
    # Dedicated binding: never reset the mature skill's other app configuration.
    cfg=Path(os.environ.get('YINGDAO_ATTENDANCE_DEMO_CONFIG',ROOT/'.local/video-demo/config.json')).resolve()
    original=settings.load()
    os.environ['YINGDAO_BRIDGE_CONFIG']=str(cfg)
    if not cfg.exists(): settings.save({k:v for k,v in original.items() if k in ('cli_path','catalog_dir')})
    TARGET_APP=settings.load().get('binding',{}).get('app_id')
    if not TARGET_APP and not allow_unbound:raise RuntimeError('Run attendance_video.py setup --app-id <your current saved Studio app ID> first')

def setup(app_id):
    global TARGET_APP
    configure(allow_unbound=True);result=bridge.bind(app_id);TARGET_APP=app_id
    return {'status':'configured','app_id':app_id,'config':str(settings.config_path()),'binding':result}

def execute(action, source, session):
    source=source.resolve(strict=True); session=session.resolve()
    record_path=session/'session.json'
    if action=='prepare':
        if record_path.exists(): return json.loads(record_path.read_text(encoding='utf-8'))
        rows=read_rows(source)
        session.mkdir(parents=True,exist_ok=True)
        output=session/'考勤筛选结果.xlsx'
        if output.exists(): raise ValueError('Output already exists; choose a new session directory')
        record={'status':'prepared','source':str(source),'output':str(output),'input_sha256':digest(source),
                'expected':[r for r in rows[1:] if float(r[3])>0], 'target_app':TARGET_APP}
        bridge.dump(session/'plan.json',make_plan(source,output,rows))
        bridge.dump(record_path,record)
        return record
    record=json.loads(record_path.read_text(encoding='utf-8'))
    if str(source)!=record['source'] or digest(source)!=record['input_sha256']:
        raise ValueError('Input differs from prepared session')
    configure()
    current=bridge.cli_current()['data']
    if current.get('app',{}).get('app_id')!=TARGET_APP:
        raise RuntimeError('Open the saved Studio app explicitly bound for this example; current app differs. No Studio mutation sent.')
    if record.get('target_app') not in (None,TARGET_APP):raise RuntimeError('Prepared session belongs to a different app')
    record['target_app']=TARGET_APP
    if action in ('build','resume'):
        if action=='build' and record['status']!='prepared': raise ValueError('Session already attempted; use launch on the SAME directory')
        if action=='build' and current['app'].get('has_unsaved_changes'):
            raise RuntimeError('Save current edits before demo build')
        if action=='build':
            bridge.bind(TARGET_APP)
            record['status']='create_requested'; bridge.dump(record_path,record)
            created=bridge.create_flow('考勤筛选演示_'+session.name)
            record.update(flow_id=created['flow_id'],status='building');bridge.dump(record_path,record)
        plan=json.loads((session/'plan.json').read_text(encoding='utf-8'))
        plan['flow_id']=record['flow_id'];bridge.dump(session/'plan.json',plan)
        journal=None
        if action=='resume':
            candidates=[]
            for path in (settings.state_dir()/'builds').glob('*.json'):
                saved=json.loads(path.read_text(encoding='utf-8'))
                if saved.get('flow_id')==record['flow_id'] and saved.get('app_id')==TARGET_APP:
                    candidates.append(path)
            if len(candidates)!=1: raise RuntimeError('No unique build journal; inspect evidence, do not recreate')
            journal=candidates[0]
        record['build']=build_plan(plan,resume=journal);bridge.dump(record_path,record)
        actual=bridge.inspect_flow(record['flow_id']);bridge.dump(session/'readback.json',actual)
        differences=compare_plan(plan,actual);bridge.dump(session/'differences.json',differences)
        if differences: raise ValueError('Readback mismatch; do not run: '+repr(differences))
        record['status']='built';bridge.dump(record_path,record)
    elif action=='run':
        if record['status']!='built': raise ValueError('Run allowed once after successful build; use check for pending run')
        if Path(record['output']).exists(): raise ValueError('Output predates run; use a new session')
        plan=json.loads((session/'plan.json').read_text(encoding='utf-8'))
        if compare_plan(plan,bridge.inspect_flow(record['flow_id'])): raise ValueError('Flow changed since build')
        record['status']='run_requested';bridge.dump(record_path,record)
        result=bridge.run_flow(record['flow_id'],20)
        record['run']=result;record['run_id']=result.get('run_id');bridge.dump(record_path,record)
        if not result.get('run_succeeded'):
            record['status']='pending_or_failed';bridge.dump(record_path,record)
            return record
        record['verification']=verify_output(record);record['status']='verified';bridge.dump(record_path,record)
    elif action=='check':
        if not record.get('run_id'): raise ValueError('No confirmed run_id; inspect evidence, do not rerun')
        result=bridge.checked(bridge.invoke('app.run_result',{'run_id':record['run_id']}))
        record['run']=result
        if result.get('run_succeeded'):
            record['verification']=verify_output(record);record['status']='verified'
        bridge.dump(record_path,record)
    return record

def lock_file():
    import msvcrt
    path=ROOT/'.local/video-demo/worker.lock';path.parent.mkdir(parents=True,exist_ok=True)
    handle=path.open('a+b');handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0)
    try: msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:
        handle.close();return None
    return handle

def background(action,source,session):
    session=session.resolve();meta=session/'worker.json'
    if action=='status':
        record=json.loads((session/'session.json').read_text(encoding='utf-8')) if (session/'session.json').exists() else {}
        worker=json.loads(meta.read_text(encoding='utf-8')) if meta.exists() else {}
        return {'status':record.get('status','not_prepared'),'flow_id':record.get('flow_id'),
                'run_id':record.get('run_id'),'verification':record.get('verification'),
                'output':record.get('output'),'worker':worker,
                'next':'If running, query status in 10 seconds. Never edit session.json or create another directory.'}
    if action=='launch':
        execute('prepare',source,session)
        gate=lock_file()
        if gate is None:return {'status':'busy','message':'A demo worker is still running; query status only.'}
        gate.close()
        previous=json.loads(meta.read_text(encoding='utf-8')) if meta.exists() else {}
        if previous.get('state')=='starting' and time.time()-previous.get('time',0)<30:
            return {'status':'starting','message':'Query status; do not launch again.'}
        bridge.dump(meta,{'state':'starting','time':time.time()})
        with (session/'worker.log').open('ab') as log:
            process=subprocess.Popen([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'worker',
                        '--source',str(source),'--session',str(session)],stdin=subprocess.DEVNULL,
                        stdout=log,stderr=log,close_fds=True,
                        creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW)
        return {'status':'started','pid':process.pid,'session':str(session),'next':'Query status in 10 seconds; do not run build again.'}
    gate=lock_file()
    if gate is None:return {'status':'busy'}
    try:
        bridge.dump(meta,{'state':'running','pid':os.getpid(),'time':time.time()})
        record=execute('prepare',source,session)
        if record.get('run_id'):
            result=execute('check',source,session)
        else:
            if record['status']=='run_requested':raise RuntimeError('Run outcome uncertain; inspect run evidence, do not rerun')
            if record.get('flow_id'): execute('resume',source,session)
            elif record['status']=='prepared':execute('build',source,session)
            else:raise RuntimeError('Creation uncertain; inspect app and evidence, do not recreate')
            result=execute('run',source,session)
        bridge.dump(meta,{'state':'finished','status':result['status'],'time':time.time()})
        return result
    except Exception as exc:
        bridge.dump(meta,{'state':'failed','error':str(exc),'time':time.time()});raise
    finally:gate.close()

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('action',choices=['setup','prepare','build','resume','run','check','launch','status','worker'])
    p.add_argument('--app-id')
    p.add_argument('--source',type=Path)
    p.add_argument('--session',type=Path);a=p.parse_args()
    if a.action=='setup':
        if not a.app_id:p.error('--app-id is required for setup')
        try:print(json.dumps(setup(a.app_id),ensure_ascii=False,indent=2))
        except Exception as exc:print(json.dumps({'status':'incomplete','error':str(exc)},ensure_ascii=False));sys.exit(1)
        sys.exit(0)
    if a.session is None:p.error('--session is required')
    if a.action!='status' and a.source is None:
        p.error('--source is required: use the actual file supplied by the user, never a historical default')
    try: print(json.dumps((background if a.action in ('launch','status','worker') else execute)(a.action,a.source,a.session),ensure_ascii=False,indent=2))
    except Exception as exc:
        print(json.dumps({'status':'incomplete','error':str(exc)},ensure_ascii=False));sys.exit(1)
