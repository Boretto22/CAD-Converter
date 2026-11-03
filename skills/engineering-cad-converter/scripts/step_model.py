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
    allowed = {'units','fully_defined','issues','scope','datum','physical_accuracy','sources',
               'profile','dimensions','expected','vertices','features'}
    if set(model) - allowed:
        raise ValueError('Unsupported STEP fields; do not silently ignore geometry: ' + ', '.join(sorted(set(model)-allowed)))
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
    dimensions = {'rectangle': ('width','height','depth'), 'circle': ('radius','depth'),
                  'polygon': ('depth',), 'revolution': ('angle',)}.get(model.get('profile'), ())
    if model.get('profile') not in {'rectangle', 'circle', 'polygon', 'revolution'} or set(model.get('dimensions', {})) != set(dimensions):
        raise ValueError('STEP needs a supported profile and its complete explicit dimensions')
    for name in dimensions:
        dimension = model['dimensions'][name]
        value = dimension.get('value')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('STEP dimension must be finite and positive: ' + name)
        if dimension.get('source_id') not in sources or not dimension.get('locator') or not dimension.get('statement'):
            raise ValueError('Missing STEP dimension evidence: ' + name)
    validate_features(model, sources)
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
    solid, script = construct(model, cq)
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
                  limitations=['Bounded extrusion/revolution and explicitly dimensioned cuts; no hidden features inferred',
                               'Volume and bounding box do not certify all geometry',
                               'External CAD, source interpretation and manufacturing review pending'])
    engine.dump(output / 'step-check.json', result)
    engine.dump(output / 'status.json', {'status': 'DEFINED_REVIEW_PENDING'})
    # This source uses only validated numeric values; it never interpolates executable source text.
    (output / 'parametric.py').write_text(script, encoding='utf-8')
    return result


def number(dimension, sources, label, positive=False):
    if not isinstance(dimension, dict):
        raise ValueError('Missing dimension evidence: ' + label)
    value = dimension.get('value')
    if (isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value)
            or (positive and value <= 0) or dimension.get('source_id') not in sources
            or not dimension.get('locator') or not dimension.get('statement')):
        raise ValueError('Invalid dimension or missing evidence: ' + label)
    return value


def polygon_points(model, sources):
    vertices = model.get('vertices')
    if not isinstance(vertices, list) or not 3 <= len(vertices) <= 200:
        raise ValueError('Profile needs 3-200 explicitly documented vertices')
    points = [(number(p.get('x'), sources, 'vertex x'), number(p.get('y'), sources, 'vertex y'))
              for p in vertices if isinstance(p, dict)]
    if len(points) != len(vertices) or len(set(points)) != len(points):
        raise ValueError('Profile has duplicate or invalid vertices; closure is implicit')
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def on(a,b,c):
        return cross(a,b,c)==0 and min(a[0],b[0]) <= c[0] <= max(a[0],b[0]) and min(a[1],b[1]) <= c[1] <= max(a[1],b[1])
    edges=list(zip(points,points[1:]+points[:1]))
    for i,(a,b) in enumerate(edges):
        for j,(c,d) in enumerate(edges):
            if j <= i or j==i+1 or (i==0 and j==len(edges)-1):
                continue
            if ((cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0)
                    or on(a,b,c) or on(a,b,d) or on(c,d,a) or on(c,d,b)):
                raise ValueError('Profile self-intersects or touches a non-adjacent edge')
    if abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in edges)) <= 1e-12:
        raise ValueError('Profile has zero area')
    return points


def validate_features(model, sources):
    if model['profile'] in {'polygon','revolution'}:
        points = polygon_points(model,sources)
        if model['profile']=='revolution' and (model['dimensions']['angle']['value'] != 360
                or min(p[0] for p in points)<0 or min(p[1] for p in points)!=0):
            raise ValueError('Revolution requires 360 degrees, non-negative radius and bottom axial coordinate zero')
    features = model.get('features', [])
    if not isinstance(features,list) or len(features)>64 or (model['profile']=='revolution' and features):
        raise ValueError('At most 64 cuts on extruded profiles; cuts on revolutions are unsupported')
    ids=set()
    for item in features:
        if not isinstance(item,dict) or not item.get('id') or item['id'] in ids:
            raise ValueError('Features need unique IDs')
        ids.add(item['id'])
        kind=item.get('type')
        keys={'x','y','depth'} | ({'width','height'} if kind=='rectangular_pocket' else {'radius'})
        if kind not in {'through_hole','blind_hole','rectangular_pocket'} or set(item.get('dimensions',{})) != keys:
            raise ValueError('Unsupported or incompletely defined cut')
        values={k:number(v,sources,item['id']+':'+k,k not in {'x','y'}) for k,v in item['dimensions'].items()}
        depth=model['dimensions']['depth']['value']
        if (kind=='through_hole' and values['depth']!=depth) or (kind!='through_hole' and values['depth']>=depth):
            raise ValueError('Cut depth contradicts through/blind definition')


def construct(model, cq):
    # Reproducible source contains only validated numeric data and fixed operations.
    d={k:v['value'] for k,v in model['dimensions'].items()}
    code=['# Nominal geometry. Review model-step.json before engineering use.', 'import cadquery as cq']
    if model['profile']=='rectangle':
        code.append(f"result = cq.Workplane('XY').rect({d['width']!r}, {d['height']!r}).extrude({d['depth']!r})")
    elif model['profile']=='circle':
        code.append(f"result = cq.Workplane('XY').circle({d['radius']!r}).extrude({d['depth']!r})")
    else:
        points=[(p['x']['value'],p['y']['value']) for p in model['vertices']]
        if model['profile']=='polygon':
            code.append(f"result = cq.Workplane('XY').polyline({points!r}).close().extrude({d['depth']!r})")
        else:
            code.append(f"result = cq.Workplane('XZ').polyline({points!r}).close().revolve(360, (0,0), (0,1))")
    # Do not execute generated text: build using the same fixed numeric operations.
    if model['profile']=='rectangle':
        result=cq.Workplane('XY').rect(d['width'],d['height']).extrude(d['depth'])
    elif model['profile']=='circle':
        result=cq.Workplane('XY').circle(d['radius']).extrude(d['depth'])
    elif model['profile']=='polygon':
        result=cq.Workplane('XY').polyline(points).close().extrude(d['depth'])
    else:
        result=cq.Workplane('XZ').polyline(points).close().revolve(360,(0,0),(0,1))
    for feature in model.get('features',[]):
        v={k:d['value'] for k,d in feature['dimensions'].items()}
        sketch=cq.Workplane('XY').center(v['x'],v['y'])
        if feature['type']=='rectangular_pocket':
            tool=sketch.rect(v['width'],v['height']).extrude(v['depth']).translate((0,0,d['depth']-v['depth']))
            expected=v['width']*v['height']*v['depth']
            shape=f"rect({v['width']!r}, {v['height']!r})"
        else:
            tool=sketch.circle(v['radius']).extrude(v['depth']).translate((0,0,d['depth']-v['depth']))
            expected=math.pi*v['radius']**2*v['depth']
            shape=f"circle({v['radius']!r})"
        cut=result.cut(tool)
        removed=result.val().Volume()-cut.val().Volume()
        if not math.isclose(removed,expected,rel_tol=1e-7,abs_tol=1e-7) or len(cut.solids().vals())!=1 or not cut.val().isValid():
            raise ValueError('Cut crosses boundary, overlaps an earlier cut or creates invalid/multiple solids')
        result=cut
        code.append(f"tool = cq.Workplane('XY').center({v['x']!r}, {v['y']!r}).{shape}.extrude({v['depth']!r}).translate((0,0,{d['depth']-v['depth']!r}))")
        code.append('result = result.cut(tool)')
    return result, '\n'.join(code)+'\n'
