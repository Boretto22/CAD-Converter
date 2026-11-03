"""Declared coverage and self-contained visual review; never an accuracy certificate."""
import base64
import html
import json
from pathlib import Path


def coverage(model):
    entities = model.get('entities', [])
    ids = {e.get('id') for e in entities if isinstance(e, dict)}
    inventory = model.get('coverage', {}).get('inventory', [])
    entries, seen, problems, assigned = [], set(), [], set()
    for item in inventory:
        identity = item.get('id') if isinstance(item, dict) else None
        if not identity or identity in seen:
            problems.append('Inventory needs unique non-empty IDs')
            continue
        seen.add(identity)
        refs = item.get('entity_ids', [])
        disposition = item.get('disposition')
        if not item.get('locator') or not isinstance(refs, list):
            problems.append(str(identity) + ': missing locator or invalid entity list')
            refs = []
        if disposition == 'included':
            if not refs or any(ref not in ids for ref in refs):
                problems.append(str(identity) + ': included source item has no matching CAD entity')
            assigned.update(refs)
        elif disposition == 'excluded':
            if not item.get('reason') or refs:
                problems.append(str(identity) + ': exclusion needs a reason and no CAD entities')
        else:
            problems.append(str(identity) + ': source item is unresolved')
        entries.append(item)
    if inventory and ids - assigned:
        problems.append('CAD entities missing from source inventory: ' + ', '.join(sorted(str(i) for i in ids - assigned)))
    return {'basis': 'DECLARED_SOURCE_INVENTORY' if inventory else 'DECLARED_ENTITIES_ONLY',
        'automatic_completeness_proven': False, 'entries': entries, 'problems': problems,
        'entity_count': len(entities), 'outside_scope': model.get('coverage', {}).get('outside_scope', []),
        'issues': model.get('issues', []),
        'warning': 'A declared inventory cannot detect objects that were never inventoried. Review every source view.'}


def write_review(model, source, cad, output, state='DRAFT_NOT_VALIDATED'):
    output = Path(output)
    def data(path):
        return 'data:image/png;base64,' + base64.b64encode(Path(path).read_bytes()).decode('ascii') if path else ''
    payload = json.dumps({'model': model, 'coverage': coverage(model)}, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    document = '''<!doctype html><html lang="es"><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Revisión CAD</title>
<style>body{font:16px system-ui;margin:24px;background:#edf2f5;color:#17344d}button,input{margin:8px}#viewport{height:65vh;overflow:auto;background:white;border:1px solid #abc}#stage{position:relative;transform-origin:top left}img{display:block;max-width:none}#cad{position:absolute;left:0;top:0;mix-blend-mode:multiply}textarea{width:98%;height:220px}pre{white-space:pre-wrap}label{display:inline-block}</style>
<h1>Revisión de fuente y CAD</h1><p>STATE — revisión pendiente; precisión física desconocida.</p>
<label>Opacidad CAD <input id="opacity" type="range" min="0" max="1" step="0.05" value="0.5"></label>
<label>Zoom <input id="zoom" type="range" min="0.25" max="4" step="0.25" value="1"></label>
<div id="viewport"><div id="stage"><img id="source" src="SOURCE"><img id="cad" src="CAD"></div></div>
<h2>Cobertura declarada</h2><pre id="coverage"></pre><h2>Lista de revisión</h2><div id="items"></div>
<p>Las casillas son anotaciones de esta sesión visual; no certifican el archivo ni modifican el CAD.</p>
<h2>Corregir borrador</h2><p>Edita el JSON y descarga el borrador. Debe volver a pasar las comprobaciones antes de exportar.</p>
<textarea id="model" aria-label="Modelo JSON"></textarea><button id="save">Descargar borrador</button><p id="message"></p>
<script type="application/json" id="data">PAYLOAD</script><script>
const data=JSON.parse(document.getElementById('data').textContent);
document.getElementById('coverage').textContent=JSON.stringify(data.coverage,null,2);
document.getElementById('model').value=JSON.stringify(data.model,null,2);
for(const entity of data.model.entities||[]){const label=document.createElement('label'),box=document.createElement('input');box.type='checkbox';label.append(box,document.createTextNode(String(entity.id)+' — '+String(entity.type)));document.getElementById('items').append(label,document.createElement('br'));}
document.getElementById('opacity').oninput=e=>document.getElementById('cad').style.opacity=e.target.value;
document.getElementById('cad').style.opacity='0.5';
document.getElementById('zoom').oninput=e=>{document.getElementById('stage').style.transform='scale('+Number(e.target.value)+')';};
document.getElementById('save').onclick=()=>{try{const model=JSON.parse(document.getElementById('model').value);const blob=new Blob([JSON.stringify(model,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='draft-model.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);document.getElementById('message').textContent='Borrador descargado. Validación pendiente.';}catch(e){document.getElementById('message').textContent='JSON no válido: '+e.message;}};
</script></html>'''
    document = document.replace('STATE', html.escape(state)).replace('SOURCE', data(source)).replace('CAD"', data(cad) + '"').replace('PAYLOAD', payload)
    (output / 'review.html').write_text(document, encoding='utf-8')
    (output / 'coverage.json').write_text(json.dumps(coverage(model), ensure_ascii=False, indent=2), encoding='utf-8')


def preview(model_path, output):
    from . import cad_pipeline as engine, recovery
    import ezdxf
    model_path, output = Path(model_path).resolve(), Path(output).resolve()
    model = json.loads(model_path.read_text(encoding='utf-8-sig'))
    engine.finite_tree(model)
    if output.exists():
        raise FileExistsError(output)
    source = (model_path.parent / model['source_image']).resolve()
    from PIL import Image
    with Image.open(source) as image:
        size = image.size
    warnings, cad = [], None
    doc = ezdxf.new('R2013')
    try:
        transform, _ = engine.registration(model)
        for item in model.get('entities', []):
            engine.make_entity(doc.modelspace(), item, {'layer': '0', 'color': 7})
        output.mkdir(parents=True, exist_ok=False)
        cad = output / 'draft-cad.png'
        engine.render_registered(doc, size, transform, cad)
    except (KeyError, ValueError, TypeError) as exc:
        warnings.append(str(exc))
        output.mkdir(parents=True, exist_ok=True)
    recovery.checkpoint(model_path, output / 'session.zip')
    import zipfile
    with zipfile.ZipFile(output / 'session.zip') as archive:
        portable = json.loads(archive.read('model.json'))
    write_review(portable, source, cad, output)
    result = {'state': 'DRAFT_NOT_VALIDATED', 'warnings': warnings, 'coverage': coverage(model),
              'next': 'Correct the draft and run engcad check. Preview is not engineering validation.'}
    engine.dump(output / 'draft-report.json', result)
    return result
