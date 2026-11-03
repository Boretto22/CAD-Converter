"""Compare candidate DXFs with independently supplied reference DXFs, including position."""
import json
import math
from pathlib import Path
from . import cad_pipeline as engine


def distance(a, b):
    if a.dxftype() != b.dxftype():
        return math.inf
    if a.dxftype() == 'LINE':
        return min(max(a.dxf.start.distance(b.dxf.start), a.dxf.end.distance(b.dxf.end)),
                   max(a.dxf.start.distance(b.dxf.end), a.dxf.end.distance(b.dxf.start)))
    if a.dxftype() == 'CIRCLE':
        return max(a.dxf.center.distance(b.dxf.center), abs(a.dxf.radius - b.dxf.radius))
    if a.dxftype() == 'ARC':
        def endpoint(e, angle):
            from ezdxf.math import Vec3
            return e.dxf.center + Vec3(math.cos(math.radians(angle)), math.sin(math.radians(angle)), 0) * e.dxf.radius
        return max(a.dxf.center.distance(b.dxf.center), abs(a.dxf.radius-b.dxf.radius),
                   endpoint(a, a.dxf.start_angle).distance(endpoint(b, b.dxf.start_angle)),
                   endpoint(a, a.dxf.end_angle).distance(endpoint(b, b.dxf.end_angle)),
                   abs(((a.dxf.end_angle-a.dxf.start_angle) % 360)-((b.dxf.end_angle-b.dxf.start_angle) % 360)) * math.pi/180 * max(a.dxf.radius,b.dxf.radius))
    return math.inf


def compare(reference, candidate, units, tolerance):
    import ezdxf
    codes = {'mm': 4, 'cm': 5, 'm': 6, 'in': 1}
    if units not in codes or isinstance(tolerance, bool) or not isinstance(tolerance, (int,float)) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('Benchmark needs units and an explicit positive numerical tolerance')
    a, b = ezdxf.readfile(reference), ezdxf.readfile(candidate)
    if a.units != codes[units] or b.units != codes[units]:
        raise ValueError('Benchmark DXF units must match the declared comparison units')
    aa, bb = list(a.modelspace()), list(b.modelspace())
    unsupported = sorted({e.dxftype() for e in aa+bb} - {'LINE','CIRCLE','ARC'})
    if len(aa) > 500 or len(bb) > 500:
        raise ValueError('Benchmark exceeds 500 entities; split the comparison scope')
    edges = [[j for j,y in enumerate(bb) if distance(x,y) <= tolerance] for x in aa]
    matches = {}
    # Bipartite augmenting paths avoid incorrect greedy assignments of nearby entities.
    def match(i, visited):
        for j in edges[i]:
            if j in visited:
                continue
            visited.add(j)
            if j not in matches or match(matches[j], visited):
                matches[j] = i
                return True
        return False
    matched = sum(match(i, set()) for i in range(len(aa))) if not unsupported else 0
    errors = len(a.audit().errors) + len(b.audit().errors)
    passed = bool(aa) and not unsupported and matched == len(aa) == len(bb) and not errors
    return {'pass': passed, 'reference_entities': len(aa), 'candidate_entities': len(bb), 'matched_entities': matched,
            'unsupported_types': unsupported, 'audit_errors': errors, 'tolerance': tolerance, 'units': units,
            'reference_sha256': engine.sha(reference), 'candidate_sha256': engine.sha(candidate),
            'note': 'Geometry comparison to the supplied reference only; reference authority and physical accuracy need separate review.'}


def run(manifest, output):
    path, output = Path(manifest).resolve(), Path(output).resolve()
    spec = json.loads(path.read_text(encoding='utf-8-sig'))
    cases = spec.get('cases', [])
    if not cases or len(cases) > 100:
        raise ValueError('Supply 1-100 benchmark cases with independently documented references')
    reports, seen = [], set()
    for case in cases:
        if not case.get('id') or case['id'] in seen or case.get('kind') not in {'real','synthetic'} or not case.get('reference_basis'):
            raise ValueError('Benchmark cases need unique IDs, real/synthetic kind and reference provenance')
        seen.add(case['id'])
        source = path.parent / case['source']
        result = compare(path.parent / case['reference_dxf'], path.parent / case['candidate_dxf'], case['units'], case['tolerance'])
        reports.append({'id': case['id'], 'kind': case['kind'], 'reference_basis': case['reference_basis'],
                        'source_sha256': engine.sha(source), **result})
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    report = {'cases': reports, 'all_pass': all(c['pass'] for c in reports),
              'real_cases': sum(c['kind']=='real' for c in reports), 'physical_accuracy': 'unknown'}
    engine.dump(output / 'benchmark.json', report)
    return report
