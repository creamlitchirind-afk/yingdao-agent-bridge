"""Build a source-only ZIP with a strict whitelist and manifest."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=['README.md','SKILL.md','LICENSE','THIRD_PARTY.md','.gitignore','config.example.json','requirements.txt','requirements-dev.txt']
DIRS=['scripts','examples','docs','tests','tools']

def main():
    files=[ROOT/f for f in FILES]
    for folder in DIRS:
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in {'.py','.md','.json'} and '__pycache__' not in p.parts)
    files.extend((ROOT/'examples/attendance/data').rglob('*.xlsx'))
    files=sorted(set(files))
    manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    output=ROOT/'dist';output.mkdir(exist_ok=True)
    archive=output/'yingdao-agent-bridge-0.2.0-preview.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files: z.write(p,'yingdao-agent-bridge/'+p.relative_to(ROOT).as_posix())
        z.writestr('yingdao-agent-bridge/MANIFEST.json',json.dumps(manifest,indent=2))
    print(json.dumps({'archive':str(archive),'source_files':len(files),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},ensure_ascii=False))

if __name__=='__main__': main()
