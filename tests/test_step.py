import json
import math
from pathlib import Path
import pytest
from engineering_cad_converter import step_model, cad_pipeline as engine


@pytest.fixture
def step_case(tmp_path):
    source = tmp_path / 'dimensions.txt'
    source.write_text('Synthetic nominal test: centered rectangle 20 x 10 mm, depth 5 mm. No other features.', encoding='utf-8')
    model = dict(units='mm', fully_defined=True, issues=[], scope='Synthetic rectangular prism',
                 datum='XY profile centered at origin; Z=0 bottom, +Z depth', physical_accuracy='unknown',
                 sources=[dict(id='S1', path='dimensions.txt', sha256=engine.sha(source))], profile='rectangle',
                 dimensions={k: dict(value=v, source_id='S1', locator='line 1', statement=f'{k}={v} mm, synthetic definition')
                             for k, v in dict(width=20, height=10, depth=5).items()},
                 expected=dict(units='mm', solids=1, volume_mm3=1000, bbox_mm=[20,10,5],
                               tolerances=dict(volume_mm3=1e-6, bbox_mm=1e-6), basis='20*10*5 from source; numerical tolerance'))
    path = tmp_path / 'step.json'; engine.dump(path, model)
    return path, model


@pytest.mark.parametrize('change', [
    lambda m: m['dimensions'].pop('depth'),
    lambda m: m['dimensions']['depth'].update(value=0),
    lambda m: m['dimensions']['depth'].update(value=float('nan')),
    lambda m: m['dimensions']['depth'].update(source_id='unknown'),
    lambda m: m.update(profile='freeform'),
    lambda m: m.update(units='in'),
    lambda m: m.update(fully_defined=False),
    lambda m: m['expected'].pop('basis'),
])
def test_step_blocked(change, step_case):
    path, model = step_case; change(model)
    path.write_text(json.dumps(model), encoding='utf-8')
    with pytest.raises((ValueError, KeyError, TypeError)):
        step_model.validate(path)


@pytest.mark.parametrize('profile', ['rectangle','circle'])
def test_step_round_trip(profile, step_case, tmp_path):
    pytest.importorskip('cadquery')
    path, model = step_case
    if profile == 'circle':
        source = path.parent / 'dimensions.txt'
        source.write_text('Synthetic cylinder: radius=3 mm, depth=5 mm, centered XY and +Z extrusion.', encoding='utf-8')
        model['sources'][0]['sha256'] = engine.sha(source)
        model['profile'] = profile
        model['dimensions'] = {k: dict(value=v, source_id='S1', locator='Synthetic additional fixture definition', statement='Fixture radius=3, depth=5 mm')
                               for k,v in dict(radius=3, depth=5).items()}
        model['expected'].update(volume_mm3=math.pi*9*5, bbox_mm=[6,6,5], basis='pi*3^2*5 from independent synthetic specification')
    engine.dump(path, model)
    result = step_model.build(path, tmp_path / 'output')
    assert result['properties_match'] and result['solids'] == 1
    assert result['status'] == 'DEFINED_REVIEW_PENDING'
    step_model.validate(tmp_path / 'output' / 'model-step.json')
    with pytest.raises(FileExistsError):
        step_model.build(path, tmp_path / 'output')


def test_bad_step_expectation_keeps_failure(step_case, tmp_path):
    pytest.importorskip('cadquery')
    path, model = step_case
    model['expected']['volume_mm3'] = 2000; engine.dump(path, model)
    with pytest.raises(ValueError):
        step_model.build(path, tmp_path / 'failed')
    status = json.loads((tmp_path / 'failed' / 'status.json').read_text())
    assert status['status'] == 'INCOMPLETE_DO_NOT_USE'


def test_step_all_solids_counted(tmp_path):
    cq = pytest.importorskip('cadquery')
    from engineering_cad_converter import check_step
    first = cq.Workplane('XY').box(1, 1, 1).val()
    second = cq.Workplane('XY').box(1, 1, 1).translate((5, 0, 0)).val()
    compound = cq.Compound.makeCompound([first, second])
    target = tmp_path / 'two.step'
    cq.exporters.export(compound, str(target))
    result = check_step.check(target)
    assert result['solids'] == 2
    assert result['volume_mm3'] == pytest.approx(2)
