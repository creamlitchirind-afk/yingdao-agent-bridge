"""Install a small local pointer skill without copying account bindings into release files."""
import argparse
import json
from pathlib import Path
import shutil
import sys

def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser()
    parser.add_argument('--skills-dir',type=Path,default=Path.home()/'.kunar'/'workspaces'/'default'/'skills')
    args=parser.parse_args()
    destination=args.skills_dir/'yingdao-agent-bridge'
    if destination.exists(): raise SystemExit('Destination exists; inspect it before replacing. Existing skill left untouched.')
    python=root/'.venv'/'Scripts'/'python.exe'
    if not python.exists(): raise SystemExit('Create repository .venv and install requirements first.')
    (destination/'scripts').mkdir(parents=True)
    (destination/'.local').mkdir()
    for filename in ['SKILL.md','README.md']:
        shutil.copy2(root/filename,destination/filename)
    shutil.copytree(root/'docs',destination/'docs')
    shutil.copy2(root/'scripts'/'agent_entry.py',destination/'scripts'/'agent_entry.py')
    (destination/'.local'/'runtime.json').write_text(json.dumps({'repo':str(root),'python':str(python),'config':str(root/'.local'/'config.json')},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'installed':str(destination),'note':'Keep repository in place. Restart/reload Kunar skill discovery as needed.'},ensure_ascii=False))

if __name__=='__main__': main()
