"""Create deterministic source/plugin/skill ZIPs from an explicit product allowlist."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = {'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'CHANGELOG.md', 'CONTRIBUTING.md',
             'pyproject.toml', 'MANIFEST.in', 'requirements.txt', 'requirements-tested.txt', 'plugin.json', '.gitignore', '.dockerignore'}
DIRECTORIES = {'skills', 'docs', 'examples', 'tests', 'tools', '.github', 'browser_service'}
EXCLUDE = {'__pycache__', '.pytest_cache', '.git', '.venv', 'build', 'dist'}


def selected(root):
    files = []
    for file in root.rglob('*'):
        rel = file.relative_to(root)
        if file.is_file() and (rel.as_posix() in TOP_FILES or rel.parts[0] in DIRECTORIES):
            if rel.parts[0] == 'browser_service':
                allowed_roots = {'engcad_web', 'tests', 'plugin', 'deploy'}
                allowed_files = {'Dockerfile', 'pyproject.toml', 'README.md', 'ACTIVAR.md', 'VALIDATION.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
                                 'validation-results.json', 'requirements-tested.txt', 'review-cases.json',
                                 'configure_plugin.py', 'package_browser_service.py'}
                if (len(rel.parts) == 2 and file.name not in allowed_files) or (len(rel.parts) > 2 and rel.parts[1] not in allowed_roots):
                    continue
            if any(p in EXCLUDE or p.endswith('.egg-info') for p in rel.parts) or file.suffix in {'.pyc', '.pyo', '.key', '.pem'}:
                continue
            if file.name == '.env' or file.name.startswith('.env.'):
                continue
            if file.is_symlink() or not file.resolve().is_relative_to(root.resolve()):
                raise ValueError('Refusing external/symlink package content')
            files.append(file)
    return sorted(files)


def archive(path, entries):
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for source, name in entries:
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, source.read_bytes())
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP checksum failure')


def package(output, root=ROOT):
    root, output = Path(root), Path(output)
    version = json.loads((root / 'plugin.json').read_text(encoding='utf-8'))['version']
    output.mkdir(parents=True, exist_ok=False)
    files = selected(root)
    archives = {}
    prefix = f'engineering-cad-converter-{version}'
    source = [(f, prefix + '/' + f.relative_to(root).as_posix()) for f in files]
    plugin = [(f, f.relative_to(root).as_posix()) for f in files
              if f.relative_to(root).parts[0] == 'skills' or f.name in {'plugin.json', 'LICENSE', 'THIRD_PARTY_NOTICES.md'}]
    skill = [(f, '/'.join(f.relative_to(root).parts[1:])) for f in files if f.relative_to(root).parts[0] == 'skills']
    skill += [(root / 'LICENSE', 'engineering-cad-converter/LICENSE'),
              (root / 'THIRD_PARTY_NOTICES.md', 'engineering-cad-converter/THIRD_PARTY_NOTICES.md')]
    for kind, entries in [('source', source), ('plugin', plugin), ('skill', skill)]:
        filename = f'{prefix}-{kind}.zip'
        archive(output / filename, entries)
        archives[filename] = hashlib.sha256((output / filename).read_bytes()).hexdigest()
    for filename in (f'engineering_cad_converter-{version}-py3-none-any.whl', f'engineering_cad_converter-{version}.tar.gz'):
        built = root / 'dist' / filename
        if built.is_file():
            shutil.copy2(built, output / filename)
            archives[filename] = hashlib.sha256(built.read_bytes()).hexdigest()
    (output / 'SHA256SUMS.txt').write_text(''.join(f'{digest}  {name}\n' for name, digest in archives.items()), encoding='utf-8')
    (output / 'CONTENTS.json').write_text(json.dumps({f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
                                                   for f in files}, indent=2), encoding='utf-8')
    (output / 'LEEME.txt').write_text(
        'Engineering CAD Converter v1.0\n\n'
        'Empieza descomprimiendo el ZIP source y leyendo README.md.\n'
        'Incluye ejemplos sinteticos DXF, STEP y PDF; no son planos reales certificados.\n'
        'El ZIP plugin es para el flujo de plugins de escritorio; requiere revision/publicacion de OpenAI.\n'
        'El ZIP skill contiene la skill reutilizable. El software local funciona sin ChatGPT.\n'
        'El wheel y sdist, cuando estan presentes, permiten instalar el paquete Python.\n'
        'SHA256SUMS.txt verifica los paquetes; CONTENTS.json verifica archivos del proyecto.\n'
        'No se ha publicado un repositorio GitHub ni un plugin en el directorio.\n', encoding='utf-8')
    bundle_name = f'Engineering-CAD-Converter-v{version}.zip'
    bundle_files = sorted(output.iterdir())
    archive(output / bundle_name, [(f, f.name) for f in bundle_files])
    archives[bundle_name] = hashlib.sha256((output / bundle_name).read_bytes()).hexdigest()
    with (output / 'SHA256SUMS.txt').open('a', encoding='utf-8') as stream:
        stream.write(f'{archives[bundle_name]}  {bundle_name}\n')
    return archives


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    print(json.dumps(package(p.parse_args().output), indent=2))
