import importlib.util
import json
from pathlib import Path
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name, filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'browser_service'/filename)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def test_generated_plugin_requires_real_origin(tmp_path):
    configure=module('web_plugin','configure_plugin.py').configure
    with pytest.raises(ValueError):
        configure('https://placeholder.example','Test publisher',tmp_path/'bad')
    with pytest.raises(ValueError):
        configure('http://localhost','Test publisher',tmp_path/'bad2')
    archive=configure('https://cad-public.example.net','Synthetic Publisher',tmp_path/'plugin')
    with zipfile.ZipFile(archive) as z:
        plugin=json.loads(z.read('plugin.json'))
        mcp=json.loads(z.read('mcp.json'))
        assert 'requires_local_executor' not in plugin['extensions']['com.openai']
        assert mcp['mcpServers']['cad']['type']=='streamable-http'
        assert mcp['mcpServers']['cad']['extensions']['com.openai']['auth']['client']['mode']=='cimd'
        assert 'skills/engineering-cad-web/SKILL.md' in z.namelist()


def test_web_package_is_repeatable_and_has_core(tmp_path):
    package=module('web_packaging','package_browser_service.py').package
    a,b=package(tmp_path/'a'),package(tmp_path/'b')
    assert a.read_bytes()==b.read_bytes()
    with zipfile.ZipFile(a) as z:
        names=z.namelist()
        assert any(n.endswith('browser_service/engcad_web/app.py') for n in names)
        assert any(n.endswith('browser_service/Dockerfile') for n in names)
        assert any(n.endswith('skills/engineering-cad-converter/scripts/engineering_gate.py') for n in names)
        assert not any('/work/' in n or '/.venv/' in n or '.egg-info/' in n for n in names)
