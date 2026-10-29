"""Stdlib launcher for a locally installed skill, using the configured repository venv."""
import json
import os
from pathlib import Path
import subprocess
import sys

def main():
    root=Path(__file__).resolve().parents[1]
    runtime_file=root/'.local'/'runtime.json'
    runtime=json.loads(runtime_file.read_text(encoding='utf-8')) if runtime_file.exists() else {}
    repo=Path(runtime.get('repo',root)).resolve()
    python=Path(runtime.get('python',repo/'.venv'/'Scripts'/'python.exe'))
    entries={'bridge':'scripts/yingdao.py','pdf':'examples/pdf_orders.py','sheet':'examples/sheet_records.py',
             'shop':'examples/shop_orders.py','attendance-demo':'examples/attendance_video.py'}
    if len(sys.argv)<2 or sys.argv[1] not in entries:
        raise SystemExit('Usage: agent_entry.py bridge|pdf|sheet|shop|attendance-demo [arguments]')
    if not python.is_file(): raise SystemExit('Repository Python environment missing; follow README installation.')
    env=dict(os.environ)
    env['YINGDAO_BRIDGE_CONFIG']=runtime.get('config',env.get('YINGDAO_BRIDGE_CONFIG',str(repo/'.local'/'config.json')))
    return subprocess.call([str(python),str(repo/entries[sys.argv[1]]),*sys.argv[2:]],env=env,cwd=str(repo))

if __name__=='__main__': sys.exit(main())
