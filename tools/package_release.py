"""Build a source-only ZIP with a strict whitelist and manifest."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=['VERSION','README.md','SKILL.md','LICENSE','THIRD_PARTY.md','.gitignore','config.example.json','requirements.txt','requirements-dev.txt']
DIRS=['scripts','examples','docs','tests','tools','skills']
PRIVATE_PARTS={'.local','.venv','.git','__pycache__','skill_backups'}
PRIVATE_NAMES={'config.json','runtime.json','session.json','worker.json'}

def source_files(root=ROOT):
    root=Path(root).resolve()
    files=[root/f for f in FILES]
    for folder in DIRS:
        files.extend(p for p in (root/folder).rglob('*') if p.is_file() and p.suffix in {'.py','.md','.json','.cmd'})
    files.extend((root/'examples/attendance/data').rglob('*.xlsx'))
    files.append(root/'examples/assets/shop-report-empty.xlsx')
    files=[p for p in files if not PRIVATE_PARTS.intersection(p.relative_to(root).parts) and p.name not in PRIVATE_NAMES and not p.name.startswith('~$')]
    if any(not p.resolve().is_relative_to(root) for p in files):raise ValueError('Source file resolves outside repository')
    return sorted(set(files))

def main():
    files=source_files()
    manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    output=ROOT/'dist';output.mkdir(exist_ok=True)
    version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
    archive=output/('yingdao-agent-bridge-'+version+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files: z.write(p,'yingdao-agent-bridge/'+p.relative_to(ROOT).as_posix())
        z.writestr('yingdao-agent-bridge/MANIFEST.json',json.dumps(manifest,indent=2))
    print(json.dumps({'archive':str(archive),'source_files':len(files),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},ensure_ascii=False))

if __name__=='__main__': main()
