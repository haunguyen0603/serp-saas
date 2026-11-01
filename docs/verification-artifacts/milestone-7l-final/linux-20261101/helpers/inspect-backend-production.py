import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path

manifest = json.loads(Path('/tmp/source-manifest.json').read_text(encoding='utf-8-sig'))
verified = []
for item in manifest:
    if not item['path'].startswith('backend/'):
        continue
    target = Path('/app') / item['path'].removeprefix('backend/')
    assert target.is_file(), item['path']
    assert hashlib.sha256(target.read_bytes()).hexdigest().upper() == item['sha256'], item['path']
    verified.append(item['path'])
for name in ('app.worker_main', 'app.services.ranking_alerts', 'app.services.ranking_alert_email'):
    importlib.import_module(name)
from app.services.report_renderers import _font_path, _register_fonts
_register_fonts()
assert platform.system() == 'Linux'
assert os.getuid() != 0
packages = {item.metadata['Name']: item.version for item in importlib.metadata.distributions()}
assert not any(name in packages for name in ('pytest', 'ruff', 'mypy'))
print(json.dumps({'platform': platform.platform(), 'python': platform.python_version(), 'uid': os.getuid(), 'font': str(_font_path()), 'verifiedBackendSourceFileCount': len(verified), 'rankingAlertWorkerImports': True, 'packages': dict(sorted(packages.items()))}, indent=2))
