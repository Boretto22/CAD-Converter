"""Short-lived parser/export process. Input paths are written by the service only."""
import argparse
import json
import os
from pathlib import Path
import warnings
import zipfile


def limits():
    if os.name == 'posix':
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
        resource.setrlimit(resource.RLIMIT_AS, (3*1024**3, 3*1024**3))
        resource.setrlimit(resource.RLIMIT_FSIZE, (150*1024**2, 150*1024**2))
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))


def preflight(source, config):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = config['source_pixels']
    warnings.simplefilter('error', Image.DecompressionBombWarning)
    if source.suffix == '.pdf':
        import pymupdf
        with pymupdf.open(source) as doc:
            if doc.needs_pass or not 1 <= len(doc) <= config['pages']:
                raise ValueError(f"PDF must be accessible and contain 1-{config['pages']} pages for this deployment")
            total_pixels = 0
            total_items = 0
            for page in doc:
                pixels = page.rect.width*page.rect.height*(120/72)**2
                total_pixels += pixels
                if pixels > config['page_pixels'] or total_pixels > config['total_pixels']:
                    raise ValueError('PDF page exceeds the render size limit')
                total_items += sum(len(path.get('items', [])) for path in page.get_drawings())
                if total_items > 100_000:
                    raise ValueError('PDF vector complexity exceeds this service scope; split the source')
    else:
        try:
            opened = Image.open(source)
        except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
            raise ValueError('Image exceeds this deployment pixel limit') from exc
        with opened as image:
            if not 1 <= getattr(image, 'n_frames', 1) <= config['pages']:
                raise ValueError('Too many image frames for this deployment')
            total_pixels = 0
            for n in range(getattr(image, 'n_frames', 1)):
                image.seek(n)
                total_pixels += image.width*image.height
                if image.width*image.height > config['source_pixels'] or total_pixels > config['total_pixels']:
                    raise ValueError('Image exceeds this deployment pixel limit')


def bundle(directory, name):
    with zipfile.ZipFile(directory / name, 'x', zipfile.ZIP_DEFLATED) as output:
        for path in sorted(directory.rglob('*')):
            if path.is_file() and path.name != name:
                output.write(path, path.relative_to(directory).as_posix())


def inspect(root):
    from PIL import Image
    from engineering_cad_converter import cad_pipeline as engine
    source = next(root.glob('source.*'))
    config = json.loads((root / 'limits.json').read_text())
    preflight(source, config)
    report = engine.inspect_source(source, root / 'inspection', dpi=120)
    pages = []
    for index, page in enumerate(report['pages'], start=1):
        original = root / 'inspection' / page['png']
        review = root / 'inspection' / f'review-{index:03}.png'
        with Image.open(original) as image:
            original_size = list(image.size)
            image.thumbnail((1800, 1800))
            image.convert('RGB').save(review)
            size = list(image.size)
        pages.append({'page': index, 'image': review.name, 'pixel_size': size,
                      'sha256': engine.sha(review), 'original_pixel_size': original_size,
                      'transformation': f'Page/frame {index}; source render/orientation in manifest; review resized from {original_size} to {size}; coordinates top-left, x right, y down'})
    engine.dump(root / 'inspection' / 'pages.json', pages)
    bundle(root / 'inspection', 'evidence.zip')
    return {'state': 'INSPECTED_DIMENSIONS_NOT_VERIFIED', 'source_sha256': engine.sha(source),
            'source_id': 'S1', 'pages': pages,
            'artifacts': {'evidence.zip': 'inspection/evidence.zip', 'manifest.json': 'inspection/manifest.json'},
            'next': 'Read the relevant pages, identify verified dimensions and acceptance criteria; never invent missing values.'}


def build(root, operation):
    from engineering_cad_converter import engineering_gate, step_model
    if operation == 'dxf':
        result = engineering_gate.build(root / 'model.json', root / 'output')
    else:
        result = step_model.build(root / 'model.json', root / 'output')
    bundle(root / 'output', 'delivery.zip')
    artifacts = {'delivery.zip': 'output/delivery.zip'}
    for name in ('plano.dxf', 'comprobacion.pdf', 'cad.png', 'informe.json', 'informe.md', 'engineering-check.json',
                 'pieza.step', 'step-check.json', 'parametric.py'):
        if (root / 'output' / name).is_file():
            artifacts[name] = 'output/' + name
    return {'state': 'DEFINED_REVIEW_PENDING', 'result': result, 'artifacts': artifacts,
            'next': 'Review the source interpretation, PDF and CAD in the intended application before engineering use.'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('operation', choices=['inspect', 'dxf', 'step'])
    p.add_argument('root')
    args = p.parse_args()
    root = Path(args.root).resolve()
    limits()
    try:
        result = inspect(root) if args.operation == 'inspect' else build(root, args.operation)
        (root / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    except (ValueError, KeyError, TypeError) as exc:
        (root / 'failure.json').write_text(json.dumps({'error': str(exc)[:1200]}), encoding='utf-8')
        raise SystemExit(2)
    except Exception as exc:
        (root / 'failure.json').write_text(json.dumps({'error': 'Parser/export failed; source unsupported, damaged or resource limit reached', 'error_type': type(exc).__name__}), encoding='utf-8')
        raise SystemExit(3)


if __name__ == '__main__':
    main()
