"""Install a small local pointer skill without copying account bindings into release files."""
import argparse
import json
from pathlib import Path
import shutil
import sys

SKILLS=('yingdao-agent-bridge','yingdao-shop-orders','yingdao-attendance-demo')

def install(root,skills_dir,skill=SKILLS[0],update=False):
    root=Path(root).resolve();skills_dir=Path(skills_dir).resolve()
    if skill not in SKILLS:raise ValueError('Unknown skill')
    destination=skills_dir/skill
    if destination.exists() and not update: raise SystemExit('Destination exists; use --update to back it up and refresh this skill.')
    python=root/'.venv'/'Scripts'/'python.exe'
    if not python.exists(): raise SystemExit('Create repository .venv and install requirements first.')
    backup=None
    if destination.exists():
        import datetime,uuid
        backup=skills_dir.parent/'skill_backups'/(skill+'_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6])
        shutil.copytree(destination,backup)
    (destination/'scripts').mkdir(parents=True,exist_ok=True)
    (destination/'.local').mkdir(exist_ok=True)
    skill_source=root/'SKILL.md' if skill==SKILLS[0] else root/'skills'/skill/'SKILL.md'
    shutil.copy2(skill_source,destination/'SKILL.md')
    shutil.copy2(root/'README.md',destination/'README.md')
    shutil.copytree(root/'docs',destination/'docs',dirs_exist_ok=True)
    if (root/'skills').is_dir():shutil.copytree(root/'skills',destination/'skills',dirs_exist_ok=True)
    shutil.copy2(root/'scripts'/'agent_entry.py',destination/'scripts'/'agent_entry.py')
    (destination/'.local'/'runtime.json').write_text(json.dumps({'repo':str(root),'python':str(python),'config':str(root/'.local'/'config.json')},ensure_ascii=False,indent=2),encoding='utf-8')
    return {'installed':str(destination),'backup':str(backup) if backup else None,'note':'Keep repository in place. Restart/reload Kunar skill discovery as needed.'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--skills-dir',type=Path,default=Path.home()/'.kunar'/'workspaces'/'default'/'skills')
    parser.add_argument('--skill',choices=SKILLS,default=SKILLS[0])
    parser.add_argument('--update',action='store_true',help='Back up this installed skill before refreshing it; leaves Kunar enablement unchanged.')
    args=parser.parse_args()
    print(json.dumps(install(Path(__file__).resolve().parents[1],args.skills_dir,args.skill,args.update),ensure_ascii=False))

if __name__=='__main__': main()
