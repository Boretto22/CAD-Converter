import copy
import json
import math
import shutil
from pathlib import Path
import pytest
import ezdxf
from engineering_cad_converter import engineering_gate as gate, cad_pipeline as engine, assurance


def test_legacy_gate_regressions(fixture_case):
    results = json.loads((fixture_case / 'results.json').read_text(encoding='utf-8'))
    assert len(results['passed']) == 25


@pytest.mark.parametrize('change', [
    lambda m: m['engineering'].pop('uncertainty'),
    lambda m: m['engineering']['uncertainty'].update(physical_accuracy=0),
    lambda m: m['engineering']['review_image'].update(sha256='wrong'),
    lambda m: m['engineering']['review_image'].update(source_id='absent'),
    lambda m: m['engineering']['review_image'].update(transformation=''),
    lambda m: m['entities'][0]['end'].__setitem__(0, float('nan')),
    lambda m: m['entities'][0]['end'].__setitem__(0, float('inf')),
    lambda m: m['entities'][0].update(type='SOLID_UNKNOWN'),
    lambda m: m['controls'][0].update(tolerance=True),
    lambda m: m['calibration'].update(status='unscaled'),
    lambda m: m['calibration'].update(evidence_ids=[]),
])
def test_reject_bad_inputs(change, model, fixture_case):
    change(model)
    path = fixture_case / 'mutated.json'
    path.write_text(json.dumps(model), encoding='utf-8')
    with pytest.raises((ValueError, KeyError, TypeError)):
        gate.check(path)


def bounded(model):
    model['engineering']['comparison_tolerance'] = 1.0
    model['engineering']['uncertainty'] = dict(mode='bounded_measurement', units='mm', basis='Synthetic interval test',
        localization_px=0.5, reference_length=100, reference_length_bound=0.1,
        reference_span_px=500, reference_span_bound_px=1, max_span_px=500, distortion_bound=0.05)
    return model


def test_uncertainty_numeric_bound(model, fixture_case):
    result = assurance.validate(bounded(model), fixture_case)
    # Worst-case scale = 100.1/499; localization + scale contribution + distortion.
    expected = 100.1/499 + 500 * (100.1/499-0.2) + 0.05
    assert result['length_error_bound'] == pytest.approx(expected)


@pytest.mark.parametrize('change', [
    lambda m: m['engineering'].update(comparison_tolerance=0.001),
    lambda m: m['engineering']['uncertainty'].update(reference_span_bound_px=500),
    lambda m: m['engineering']['uncertainty'].update(reference_length_bound=100),
    lambda m: m['engineering']['uncertainty'].update(localization_px=-1),
    lambda m: m['engineering']['uncertainty'].update(units='in'),
    lambda m: m['engineering']['uncertainty'].update(reference_length=200),
    lambda m: m['engineering']['uncertainty'].update(max_span_px=10),
    lambda m: m['engineering']['uncertainty'].update(localization_px=0, reference_length_bound=0, reference_span_bound_px=0, distortion_bound=0),
])
def test_uncertainty_rejections(change, model, fixture_case):
    bounded(model); change(model)
    with pytest.raises(ValueError):
        assurance.validate(model, fixture_case)


def test_portable_delivery(fixture_case, tmp_path):
    destination = tmp_path / 'relocated'
    shutil.copytree(fixture_case / 'export', destination)
    report = gate.check(destination / 'modelo-reproducible.json')
    assert report['status'] == 'STRUCTURED_EVIDENCE_CHECKED_REVIEW_PENDING'
    doc = ezdxf.readfile(destination / 'plano.dxf')
    assert doc.units == 4
    assert len(doc.modelspace()) == 2
    assert doc.modelspace().query('LINE')[0].dxf.start.distance(doc.modelspace().query('LINE')[0].dxf.end) == 100
    assert doc.modelspace().query('CIRCLE')[0].dxf.radius == 10


def test_no_overwrite(fixture_case):
    before = engine.sha(fixture_case / 'export' / 'plano.dxf')
    with pytest.raises(FileExistsError):
        gate.build(fixture_case / 'model.json', fixture_case / 'export')
    assert before == engine.sha(fixture_case / 'export' / 'plano.dxf')


def test_multipage_pdf_inspection(tmp_path):
    import pymupdf
    pdf = pymupdf.open()
    for i in range(2):
        page = pdf.new_page()
        page.draw_line((10, 10), (100, 100))
        page.insert_text((30, 50), f'Page {i+1}')
    source = tmp_path / 'vector.pdf'
    pdf.save(source); pdf.close()
    report = engine.inspect_source(source, tmp_path / 'inspection', dpi=72)
    assert len(report['pages']) == 2
    assert all(page['vector_paths'] >= 1 for page in report['pages'])
    assert report['sha256'] == engine.sha(tmp_path / 'inspection' / 'original.pdf')


def test_corrupt_source(tmp_path):
    source = tmp_path / 'broken.png'; source.write_bytes(b'not an image')
    with pytest.raises(OSError):
        engine.inspect_source(source, tmp_path / 'broken-output')


def test_visual_registration(fixture_case):
    from PIL import Image
    # CAD line at (100,400)-(600,400); read a patch well away from other geometry.
    with Image.open(fixture_case / 'export' / 'cad.png') as image:
        assert image.convert('L').crop((350, 396, 355, 405)).getextrema()[0] < 180
        assert image.convert('L').crop((350, 300, 355, 305)).getextrema()[0] > 240


@pytest.mark.parametrize('unit,factor,code', [('cm',0.1,5),('m',0.001,6),('in',1/25.4,1)])
def test_explicit_unit_conversion(unit, factor, code, model, fixture_case, tmp_path):
    model['units'] = unit
    for entity in model['entities']:
        for key in ('start','end','center'):
            if key in entity:
                entity[key] = [x*factor for x in entity[key]]
        if 'radius' in entity:
            entity['radius'] *= factor
    for anchor in model['registration']['anchors']:
        anchor['cad'] = [x*factor for x in anchor['cad']]
    for control in model['controls']:
        control['expected'] *= factor
    for evidence in model['engineering']['evidence']:
        if evidence['kind'] == 'dimension':
            evidence['normalized_value'] *= factor
            evidence['normalized_units'] = unit
            evidence['statement'] += f'; explicit mm to {unit} factor {factor}'
    path = fixture_case / f'model-{unit}.json'; engine.dump(path, model)
    output = tmp_path / 'converted'; gate.build(path, output)
    doc = ezdxf.readfile(output / 'plano.dxf')
    assert doc.units == code
    assert doc.modelspace().query('CIRCLE')[0].dxf.radius == pytest.approx(10*factor)


def test_partial_export_is_marked(monkeypatch, fixture_case, tmp_path):
    def render_failure(*args, **kwargs):
        raise RuntimeError('Simulated renderer failure')
    monkeypatch.setattr(engine, 'render_registered', render_failure)
    output = tmp_path / 'failed'
    with pytest.raises(RuntimeError):
        gate.build(fixture_case / 'model.json', output)
    assert json.loads((output / 'status.json').read_text())['status'] == 'INCOMPLETE_DO_NOT_USE'
