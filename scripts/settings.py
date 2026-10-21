"""Portable, local-only configuration and installation discovery."""
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

def config_path():
    return Path(os.environ.get('YINGDAO_BRIDGE_CONFIG', ROOT / '.local' / 'config.json')).resolve()

def load():
    path = config_path()
    data = json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    if not isinstance(data, dict):
        raise ValueError('Configuration must be a JSON object')
    return data

def save(data):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)

def state_dir():
    value = load().get('state_dir')
    path = Path(value).expanduser() if value else config_path().parent / 'state'
    if not path.is_absolute():
        path = config_path().parent / path
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()

def cli_path():
    explicit = os.environ.get('YINGDAO_CLI') or load().get('cli_path')
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_file():
            raise FileNotFoundError('Configured CLI does not exist: ' + str(p))
        return p.resolve()
    candidates = []
    found = shutil.which('shadowbot.shell-cli.exe')
    if found:
        candidates.append(Path(found))
    for key in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
        if os.environ.get(key):
            candidates.append(Path(os.environ[key]) / 'ShadowBot' / 'shadowbot.shell-cli.exe')
    if os.name == 'nt':
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r'Software\Microsoft\Windows\CurrentVersion\App Paths\ShadowBot.exe') as key:
                    candidates.append(Path(winreg.QueryValue(key, None)).parent / 'shadowbot.shell-cli.exe')
            except OSError:
                pass
        # Only known installation locations; never recursively scan user disks.
        for drive in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            candidates.append(Path(drive + ':/Program Files/ShadowBot/shadowbot.shell-cli.exe'))
    existing = list(dict.fromkeys(p.resolve() for p in candidates if p.is_file()))
    if len(existing) != 1:
        raise RuntimeError('CLI discovery found %d installations. Set YINGDAO_CLI or cli_path in config.' % len(existing))
    return existing[0]

def catalog_dir():
    explicit = load().get('catalog_dir')
    if explicit:
        base = Path(explicit).expanduser().resolve()
    else:
        installs = list(cli_path().parent.glob('shadowbot-*/Resources/Copilot/knowledge/visual-blocks'))
        # Do not silently choose the newest directory when several installed versions coexist.
        if len(installs) != 1:
            raise RuntimeError('Multiple/no local catalogs; configure catalog_dir for the running Studio version.')
        base = installs[0]
    for filename in ('block_catalog.md', 'block_detail.md'):
        if not (base / filename).is_file():
            raise FileNotFoundError(str(base / filename))
    return base

def definitions():
    result = {}
    for line in (catalog_dir() / 'block_detail.md').read_text(encoding='utf-8').splitlines():
        if line.startswith('<') and '>' in line:
            name, rest = line[1:].split('>', 1)
            try:
                result[name] = json.JSONDecoder().raw_decode(rest)[0]
            except ValueError:
                pass
    return result
