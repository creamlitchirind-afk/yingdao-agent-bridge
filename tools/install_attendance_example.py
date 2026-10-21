"""Create a new bound Yingdao code flow; save only, never run automatically."""
from pathlib import Path
import argparse,sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import studio_bridge as bridge

def main():
 p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');p.add_argument('--name',default='三周考勤汇总示例');a=p.parse_args()
 if not a.write:raise SystemExit('Use --write to create and save a new flow.')
 bridge.guard()
 current=bridge.cli_current()['data']
 if current['app']['has_unsaved_changes']:raise SystemExit('Save current application before installing the example.')
 command=[sys.executable,'-I','-X','utf8',str(ROOT/'examples/attendance/run_demo.py')]
 # -I removes the script directory from sys.path, so explicitly insert the trusted repo directory.
 code="import subprocess\ndef main(args):\n    command = %r\n    p = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=180, creationflags=0x08000000)\n    if p.returncode: raise RuntimeError(p.stderr or p.stdout)\n    print(p.stdout)\n" % command
 result=bridge.checked(bridge.invoke('app.create_flow',{'flows':[{'flow_name':a.name,'kind':'code'}]},True))
 flow=result['results'][0]['flow_id'];bridge.remember_flow(flow)
 bridge.checked(bridge.invoke('codeflow.write',{'flow_id':flow,'content':code},True))
 bridge.checked(bridge.invoke('app.save',{},True))
 print(json.dumps({'flow_id':flow,'saved':True,'executed':False},ensure_ascii=False))
if __name__=='__main__':main()
