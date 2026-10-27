import importlib.util
import json
from pathlib import Path
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('packager', ROOT / 'tools' / 'package_release.py')
packager = importlib.util.module_from_spec(spec); spec.loader.exec_module(packager)


def test_repeatable_archives_and_layout(tmp_path):
    first = packager.package(tmp_path / 'first')
    second = packager.package(tmp_path / 'second')
    assert first == second
    with zipfile.ZipFile(tmp_path / 'first' / 'engineering-cad-converter-1.0.0-plugin.zip') as z:
        assert 'plugin.json' in z.namelist()
        assert 'skills/engineering-cad-converter/SKILL.md' in z.namelist()
        assert all('..' not in Path(n).parts and not Path(n).is_absolute() for n in z.namelist())
        assert all('__pycache__' not in n and '.venv' not in n for n in z.namelist())
        manifest = json.loads(z.read('plugin.json'))
        assert manifest['extensions']['com.openai']['requires_local_executor'] is True
    with pytest.raises(FileExistsError):
        packager.package(tmp_path / 'first')


def test_excludes_unlisted_private_files(tmp_path):
    (tmp_path / 'private.pdf').write_bytes(b'private')
    (tmp_path / '.env').write_text('SECRET=x')
    (tmp_path / 'README.md').write_text('public')
    assert [p.name for p in packager.selected(tmp_path)] == ['README.md']
