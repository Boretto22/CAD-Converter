"""Bounded v1 STEP generator: explicitly dimensioned rectangular or circular extrusion.

No reconstruction from silhouettes. No execution of user-supplied CAD scripts.
"""
import hashlib
import json
import math
from pathlib import Path
import shutil

try:
    from . import cad_pipeline as engine, check_step
except ImportError:
    import cad_pipeline as engine
    import check_step


def validate(path):
    path = Path(path).resolve()
    model = json.loads(path.read_text(encoding='utf-8-sig'))
    engine.finite_tree(model)
    if model.get('units') != 'mm' or model.get('issues') != [] or model.get('fully_defined') is not True:
        raise ValueError('STEP requires mm, explicit complete definition, and no unresolved issues')
    if not model.get('scope') or not model.get('datum') or model.get('physical_accuracy') != 'unknown':
        raise ValueError('Declare scope, datum, and unknown physical accuracy of nominal model')
    sources = {}
    for item in model.get('sources', []):
        if item['id'] in sources:
            raise ValueError('Duplicate STEP source ID')
        source = (path.parent / item['path']).resolve()
        if engine.sha(source) != item['sha256']:
            raise ValueError('STEP source hash mismatch')
        sources[item['id']] = source
    if not sources:
        raise ValueError('STEP needs preserved source evidence')
    dimensions = ('width', 'height', 'depth') if model.get('profile') == 'rectangle' else ('radius', 'depth')
    if model.get('profile') not in {'rectangle', 'circle'} or set(model.get('dimensions', {})) != set(dimensions):
        raise ValueError('v1 STEP supports only rectangle or circle extrusion with explicit dimensions')
    for name in dimensions:
        dimension = model['dimensions'][name]
        value = dimension.get('value')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('STEP dimension must be finite and positive: ' + name)
        if dimension.get('source_id') not in sources or not dimension.get('locator') or not dimension.get('statement'):
            raise ValueError('Missing STEP dimension evidence: ' + name)
    expected = model.get('expected', {})
    if not expected.get('basis') or expected.get('units') != 'mm' or expected.get('solids') != 1:
        raise ValueError('Supply independent expected properties and calculation basis')
    for key in ('volume_mm3', 'bbox_mm'):
        values = expected.get(key)
        values = values if isinstance(values, list) else [values]
        if len(values) != (3 if key == 'bbox_mm' else 1) or any(isinstance(x, bool) or not isinstance(x, (int, float)) or x <= 0 for x in values):
            raise ValueError('Invalid STEP expectation ' + key)
        tolerance = expected.get('tolerances', {}).get(key)
        if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or tolerance <= 0:
            raise ValueError('STEP requires explicit positive numerical tolerances')
    return model


def build(path, output):
    model = validate(path)
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    import cadquery as cq
    d = {key: value['value'] for key, value in model['dimensions'].items()}
    sketch = cq.Workplane('XY')
    if model['profile'] == 'rectangle':
        sketch = sketch.rect(d['width'], d['height'])
    else:
        sketch = sketch.circle(d['radius'])
    solid = sketch.extrude(d['depth'])
    # Expected properties come from the caller's independently documented calculation.
    output.mkdir(parents=True, exist_ok=False)
    engine.dump(output / 'status.json', {'status': 'INCOMPLETE_DO_NOT_USE'})
    cq.exporters.export(solid, str(output / 'pieza.step'))
    result = check_step.check(output / 'pieza.step', model['expected'])
    if not result.get('properties_match'):
        engine.dump(output / 'step-check.json', result)
        raise ValueError('STEP reimport failed expected properties; output is incomplete')
    portable = json.loads(json.dumps(model))
    (output / 'sources').mkdir()
    for i, source in enumerate(portable['sources']):
        original = (Path(path).resolve().parent / source['path']).resolve()
        name = f'source-{i+1:03}{original.suffix.lower()}'
        shutil.copy2(original, output / 'sources' / name)
        source['path'] = 'sources/' + name
    engine.dump(output / 'model-step.json', portable)
    result.update(status='DEFINED_REVIEW_PENDING', scope=model['scope'], physical_accuracy='unknown',
                  limitations=['Only simple extrusion; no hidden features inferred',
                               'Volume and bounding box do not certify all geometry',
                               'External CAD, source interpretation and manufacturing review pending'])
    engine.dump(output / 'step-check.json', result)
    engine.dump(output / 'status.json', {'status': 'DEFINED_REVIEW_PENDING'})
    # This source uses only validated numeric values; it never interpolates executable source text.
    profile = f"rect({d['width']!r}, {d['height']!r})" if model['profile'] == 'rectangle' else f"circle({d['radius']!r})"
    (output / 'parametric.py').write_text("# Generated nominal model. See model-step.json for evidence.\nimport cadquery as cq\n"
        + f"result = cq.Workplane('XY').{profile}.extrude({d['depth']!r})\n", encoding='utf-8')
    return result
