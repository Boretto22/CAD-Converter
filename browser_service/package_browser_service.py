"""Archive the actual service plus its CAD core, excluding runtime/private files."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('core_release', ROOT/'tools'/'package_release.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
EXCLUDED = {'__pycache__','.pytest_cache','.venv','build','dist','.git'}
EXTENSIONS = {'.py','.toml','.md','.yml','.txt','.sh','.json','.example'}


def package(output):
    output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    files = core.selected(ROOT)
    files += [ROOT/'.dockerignore']
    for path in (ROOT/'browser_service').rglob('*'):
        relative = path.relative_to(ROOT/'browser_service')
        if len(relative.parts) > 1 and relative.parts[0] not in {'engcad_web','tests','plugin','deploy'}:
            continue
        if path.is_file() and path.suffix in EXTENSIONS and not any(p in EXCLUDED or p.endswith('.egg-info') for p in relative.parts):
            if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
                raise ValueError('External package file')
            files.append(path)
    # Dockerfile has no suffix; explicit inclusion avoids broad inclusion of runtime files.
    files.append(ROOT/'browser_service'/'Dockerfile')
    prefix = 'Engineering-CAD-Converter-Web-v1.0.0'
    archive = output/(prefix+'.zip')
    core.archive(archive,[(f,prefix+'/'+f.relative_to(ROOT).as_posix()) for f in sorted(set(files))])
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/'SHA256SUMS.txt').write_text(digest+'  '+archive.name+'\n',encoding='utf-8')
    return archive


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True)
    print(package(p.parse_args().output))
