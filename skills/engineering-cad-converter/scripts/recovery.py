"""Portable, non-executable session checkpoints, including unfinished models."""
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
import tempfile
import zipfile

MAX_BYTES = 100 * 1024 * 1024


def checkpoint(model_path, destination):
    path, destination = Path(model_path).resolve(), Path(destination).resolve()
    model = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(model, dict):
        raise ValueError('Session model must be a JSON object')
    portable = copy.deepcopy(model)
    records, missing, files = {}, [], {}
    refs = list(portable.get('engineering', {}).get('sources', [])) + list(portable.get('sources', []))
    if portable.get('source_image'):
        refs.append({'path': portable['source_image'], '_image': True})
    for i, ref in enumerate(refs):
        source = (path.parent / ref['path']).resolve()
        if not source.is_relative_to(path.parent) or source.is_symlink():
            raise ValueError('Session source must stay inside the model directory')
        name = f'sources/{i:03}{source.suffix.lower()}'
        if not source.is_file():
            missing.append(ref['path'])
            continue
        if source.stat().st_size > MAX_BYTES:
            raise ValueError('Session source exceeds checkpoint size limit')
        data = source.read_bytes()
        if sum(len(b) for b in files.values()) + len(data) > MAX_BYTES:
            raise ValueError('Session exceeds checkpoint size limit')
        files[name] = data
        records[name] = hashlib.sha256(data).hexdigest()
        if ref.get('_image'):
            portable['source_image'] = name
        else:
            ref['path'] = name
    files['model.json'] = json.dumps(portable, ensure_ascii=False, allow_nan=False).encode('utf-8')
    records['model.json'] = hashlib.sha256(files['model.json']).hexdigest()
    files['session.json'] = json.dumps({'version': 1, 'state': 'DRAFT_NOT_VALIDATED',
        'sha256': records, 'missing_sources': missing, 'review': 'PENDING'}).encode('utf-8')
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return {'state': 'DRAFT_NOT_VALIDATED', 'missing_sources': missing, 'file': destination.name}


def resume(archive_path, output):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if len(infos) > 1000 or len(names) != len(set(names)) or sum(i.file_size for i in infos) > MAX_BYTES:
            raise ValueError('Invalid or oversized session archive')
        for i in infos:
            p = PurePosixPath(i.filename)
            if (p.is_absolute() or PureWindowsPath(i.filename).drive or '..' in p.parts
                    or '\\' in i.filename or str(p) != i.filename
                    or stat.S_ISLNK(i.external_attr >> 16) or i.is_dir()):
                raise ValueError('Unsafe session archive path')
        if 'session.json' not in names or 'model.json' not in names:
            raise ValueError('Session archive is missing its manifest or model')
        session = json.loads(archive.read('session.json'))
        if not isinstance(session, dict) or not isinstance(session.get('sha256'), dict):
            raise ValueError('Invalid session manifest')
        hashes = session['sha256']
        if session.get('version') != 1 or set(hashes) != set(names) - {'session.json'} or 'model.json' not in hashes:
            raise ValueError('Invalid session manifest')
        for name, digest in hashes.items():
            if not isinstance(digest, str) or len(digest) != 64:
                raise ValueError('Invalid session checksum')
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError('Session checksum mismatch')
        if not isinstance(json.loads(archive.read('model.json')), dict):
            raise ValueError('Session model must be a JSON object')
        # Files are data only. Never import or run a session's contents.
        with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
            stage = Path(temporary) / 'session'
            stage.mkdir()
            for name in names:
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
            stage.rename(output)
    return {'state': 'DRAFT_NOT_VALIDATED', 'model': str(output / 'model.json'),
            'missing_sources': session.get('missing_sources', []), 'next': 'Resolve missing data and run engcad check before export.'}
