import json
from pathlib import Path
import pytest
from engineering_cad_converter.selftest_engineering import main


@pytest.fixture(scope='session')
def fixture_case(tmp_path_factory):
    path = tmp_path_factory.mktemp('cad') / 'case'
    main(path)
    return path


@pytest.fixture
def model(fixture_case):
    return json.loads((fixture_case / 'model.json').read_text(encoding='utf-8'))
