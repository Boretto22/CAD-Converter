"""Evidence provenance and non-statistical uncertainty bounds."""
import math
from pathlib import Path

try:
    from . import cad_pipeline as engine
except ImportError:
    import cad_pipeline as engine


def number(value, positive=False):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and (value > 0 if positive else value >= 0))


def validate(model, base):
    """Numbers are declarations supported by cited evidence, never inferred accuracy."""
    eng = model['engineering']
    uncertainty = eng.get('uncertainty', {})
    mode = uncertainty.get('mode')
    if mode == 'nominal_definition':
        if uncertainty.get('physical_accuracy') != 'unknown' or not uncertainty.get('basis'):
            raise ValueError('Nominal definition must state physical accuracy unknown and a basis')
        result = {'mode': mode, 'physical_accuracy': 'unknown', 'basis': uncertainty['basis']}
    elif mode == 'bounded_measurement':
        keys = ('localization_px', 'reference_length', 'reference_length_bound', 'reference_span_px',
                'reference_span_bound_px', 'max_span_px', 'distortion_bound')
        if uncertainty.get('units') != model['units'] or not uncertainty.get('basis'):
            raise ValueError('Uncertainty requires units and source/method basis')
        if any(not number(uncertainty.get(k), k in {'reference_length', 'reference_span_px', 'max_span_px'}) for k in keys):
            raise ValueError('Missing or invalid uncertainty components')
        u = uncertainty
        length, span = u['reference_length'], u['reference_span_px']
        dlength, dspan = u['reference_length_bound'], u['reference_span_bound_px']
        if dlength >= length or dspan >= span:
            raise ValueError('Reference bound does not establish a positive scale')
        s = length / span
        smin, smax = (length-dlength)/(span+dspan), (length+dlength)/(span-dspan)
        _, registration = engine.registration(model)
        pixels_per_unit = registration['pixel_per_unit']
        registered_scale = 1 / pixels_per_unit
        if registered_scale < smin-1e-12 or registered_scale > smax+1e-12:
            raise ValueError('Declared measurement scale disagrees with image registration')
        for entity in model.get('entities', []):
            length_in_units = 0
            if entity['type'] == 'LINE':
                length_in_units = math.dist(entity['start'], entity['end'])
            elif entity['type'] in {'CIRCLE', 'ARC'}:
                length_in_units = 2*entity['radius']
            if length_in_units*pixels_per_unit > u['max_span_px']*(1+1e-10):
                raise ValueError('Declared maximum span is smaller than exported geometry')
        scale_error = max(smax-s, s-smin)
        bound = 2*u['localization_px']*smax + u['max_span_px']*scale_error + u['distortion_bound']
        if bound <= 0:
            raise ValueError('Physical measurement cannot declare zero uncertainty')
        if bound > eng['comparison_tolerance']:
            raise ValueError('Measurement uncertainty exceeds the declared acceptance criterion')
        result = {'mode': mode, 'length_error_bound': bound, 'units': model['units'],
                  'scale_interval': [smin, smax], 'basis': u['basis'],
                  'meaning': 'Conservative declared-component bound; not statistical confidence or certification'}
    else:
        raise ValueError('Declare nominal_definition or bounded_measurement uncertainty')
    source_image = (Path(base) / model['source_image']).resolve()
    provenance = eng.get('review_image', {})
    if provenance.get('sha256') != engine.sha(source_image):
        raise ValueError('Review image hash missing or mismatched')
    ids = {s['id'] for s in eng['sources']}
    if provenance.get('source_id') not in ids or not provenance.get('transformation'):
        raise ValueError('Review image needs source ID and transformation record')
    return result


def portable_sources(model, base, output):
    """Copy cited originals, using neutral names. Return a relocatable model."""
    import copy
    import shutil
    output = Path(output)
    directory = output / 'sources'
    directory.mkdir(exist_ok=False)
    portable = copy.deepcopy(model)
    for index, source in enumerate(portable['engineering']['sources']):
        original = (Path(base) / source['path']).resolve()
        filename = f'source-{index+1:03}{original.suffix.lower()}'
        shutil.copy2(original, directory / filename)
        source['path'] = f'sources/{filename}'
    portable['source_image'] = 'fuente.png'
    portable['engineering']['review_image']['sha256'] = engine.sha(output / 'fuente.png')
    portable['engineering']['review_image']['transformation'] += '; lossless review copy saved as fuente.png'
    return portable
