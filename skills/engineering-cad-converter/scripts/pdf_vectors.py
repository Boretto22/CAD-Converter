"""Exact PDF stroke primitives, explicitly uncalibrated; no circle/arc guessing."""
import json
from pathlib import Path
from . import cad_pipeline as engine


def extract(source, output, page=1):
    import ezdxf
    import pymupdf
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    if not source.is_file():
        raise ValueError('No existe el archivo de entrada')
    try:
        pdf = pymupdf.open(source)
    except pymupdf.FileNotFoundError as exc:
        raise ValueError('No existe el archivo de entrada') from exc
    except (pymupdf.FileDataError, pymupdf.EmptyFileError) as exc:
        raise ValueError('El archivo no es un PDF valido, o esta danado') from exc
    with pdf:
        if pdf.needs_pass or isinstance(page, bool) or not 1 <= page <= len(pdf):
            raise ValueError('Invalid or inaccessible PDF page')
        view = pdf[page - 1]
        drawings = view.get_drawings(extended=True)
        doc = ezdxf.new('R2013')
        doc.units = 0
        space = doc.modelspace()
        inventory = []
        def point(p):
            # Unrotated PDF page coordinates, reflected Y; one CAD unit = one PDF point.
            return (float(p[0]), -float(p[1]))
        for n, drawing in enumerate(drawings):
            pid = f'P{page}-PATH{n+1}'
            record = {'id': pid, 'pdf_sequence': drawing.get('seqno'), 'layer': drawing.get('layer', ''),
                      'pdf_type': drawing.get('type'), 'items': [], 'limitations': []}
            inventory.append(record)
            if drawing.get('type') not in {'s', 'f', 'fs'}:
                record['limitations'].append('Clip/group operation is inventoried but not represented as CAD geometry')
                continue
            if drawing.get('type') in {'f', 'fs'}:
                record['limitations'].append('Fill appearance is not reproduced; boundary strokes only')
            first, last = None, None
            for j, item in enumerate(drawing.get('items', [])):
                eid, kind = f'{pid}-ITEM{j+1}', item[0]
                attr = {'layer': 'PDF_STROKES_UNCALIBRATED'}
                entity = None
                if kind == 'l':
                    a, b = point(item[1]), point(item[2])
                    entity = space.add_line(a, b, dxfattribs=attr)
                    first, last = (a if last != a else first), b
                elif kind == 'c':
                    controls = [point(p) for p in item[1:5]]
                    entity = space.add_open_spline(controls, degree=3,
                        knots=[0, 0, 0, 0, 1, 1, 1, 1], dxfattribs=attr)
                    first, last = (controls[0] if last != controls[0] else first), controls[-1]
                elif kind in {'re', 'qu'}:
                    shape = item[1]
                    corners = [shape.tl, shape.tr, shape.br, shape.bl] if kind == 're' else [shape.ul, shape.ur, shape.lr, shape.ll]
                    entity = space.add_lwpolyline([point(p) for p in corners], close=True, dxfattribs=attr)
                    first, last = None, None
                else:
                    record['limitations'].append(f'Unsupported PDF item {kind}; not silently approximated')
                record['items'].append({'id': eid, 'pdf_kind': kind,
                    'handle': entity.dxf.handle if entity else None,
                    'status': 'EXACT_STROKE' if entity else 'UNSUPPORTED'})
            if drawing.get('closePath') and first is not None and last != first:
                space.add_line(last, first, dxfattribs={'layer': 'PDF_STROKES_UNCALIBRATED'})
        if 'PDF_STROKES_UNCALIBRATED' not in doc.layers:
            doc.layers.new('PDF_STROKES_UNCALIBRATED')
        output.mkdir(parents=True, exist_ok=False)
        doc.saveas(output / 'pdf-strokes-UNCALIBRATED.dxf')
        reopened = ezdxf.readfile(output / 'pdf-strokes-UNCALIBRATED.dxf')
        report = {'state': 'UNCALIBRATED_GRAPHICS_NOT_NOMINAL_CAD', 'source_sha256': engine.sha(source),
            'page': page, 'coordinate_system': 'Unrotated PDF page x right, y reflected; units are PDF points, not model millimetres',
            'paths': inventory, 'exported_entities': len(reopened.modelspace()),
            'audit_errors': len(reopened.audit().errors), 'text_blocks': len(view.get_text('blocks')),
            'raster_images': len(view.get_image_info()), 'review': 'PENDING',
            'limitations': ['Text, raster content, clipping, fill appearance and stroke styling are not converted',
                'PDF Beziers remain cubic splines; no circles or manufacturing dimensions inferred',
                'Explicit dimensional calibration and source authority are required before nominal engineering export']}
        engine.dump(output / 'vector-inventory.json', report)
        return report
