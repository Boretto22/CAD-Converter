import copy
import json
from pathlib import Path
import zipfile
import pytest
from engineering_cad_converter import cad_pipeline as engine, cli, recovery, review, pdf_vectors, benchmark


def test_corrupt_pdf_cli_is_atomic_and_readable(tmp_path, capsys):
    source = tmp_path / 'bad.pdf'
    source.write_bytes(b'not a pdf')
    with pytest.raises(SystemExit) as error:
        cli.main(['inspect', str(source), str(tmp_path / 'output')])
    assert error.value.code == 2
    text = capsys.readouterr().err
    assert 'BLOQUEADO:' in text and 'Traceback' not in text
    assert not (tmp_path / 'output').exists()


def test_inspection_never_overwrites_existing_output(tmp_path):
    source = tmp_path / 'bad.pdf'; source.write_bytes(b'not a pdf')
    output = tmp_path / 'existing'; output.mkdir()
    (output / 'keep.txt').write_text('user data')
    with pytest.raises(FileExistsError):
        engine.inspect_source(source, output)
    assert (output / 'keep.txt').read_text() == 'user data'


def test_cli_block_prefix_is_not_duplicated(tmp_path, capsys):
    path = tmp_path / 'invalid.json'; engine.dump(path, {'units': 'mm'})
    with pytest.raises(SystemExit) as error:
        cli.main(['check', str(path)])
    assert error.value.code == 2
    assert capsys.readouterr().err.count('BLOQUEADO:') == 1


def test_checkpoint_restores_sources_and_unresolved_work(tmp_path):
    source = tmp_path / 'original.txt'; source.write_text('synthetic file content')
    path = tmp_path / 'draft.json'
    engine.dump(path, {'issues': ['Need depth'], 'sources': [{'id':'S1','path':'original.txt','sha256':engine.sha(source)}]})
    archive = tmp_path / 'session.zip'
    recovery.checkpoint(path, archive)
    restored = tmp_path / 'restored'
    result = recovery.resume(archive, restored)
    model = json.loads((restored / 'model.json').read_text())
    assert result['state'] == 'DRAFT_NOT_VALIDATED' and model['issues'] == ['Need depth']
    assert (restored / model['sources'][0]['path']).read_text() == 'synthetic file content'
    assert engine.sha(restored / model['sources'][0]['path']) == model['sources'][0]['sha256']
    with pytest.raises(FileExistsError):
        recovery.resume(archive, restored)


@pytest.mark.parametrize('name', ['../outside.txt', '/absolute.txt', 'C:/outside.txt', 'sources/../../outside', 'a\\b'])
def test_session_zip_rejects_path_traversal(tmp_path, name):
    archive = tmp_path / 'unsafe.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr(name, 'bad')
    with pytest.raises(ValueError):
        recovery.resume(archive, tmp_path / 'restored')
    assert not (tmp_path / 'restored').exists()


def test_checkpoint_refuses_external_source(tmp_path):
    path = tmp_path / 'draft.json'
    engine.dump(path, {'sources': [{'path':'../private.txt'}]})
    with pytest.raises(ValueError, match='inside'):
        recovery.checkpoint(path, tmp_path / 'session.zip')


def test_coverage_detects_missing_entities_and_unresolved_items():
    model = {'entities':[{'id':'A','type':'LINE'}], 'coverage':{'inventory':[
        {'id':'P1','locator':'page 1 line','disposition':'included','entity_ids':['missing']},
        {'id':'P2','locator':'page 1 hole','disposition':'unresolved','entity_ids':[]}]}}
    result = review.coverage(model)
    assert len(result['problems']) == 3 and not result['automatic_completeness_proven']


def test_preview_saves_incomplete_model_and_escapes_source_text(tmp_path):
    from PIL import Image
    Image.new('RGB', (80,50), 'white').save(tmp_path / 'source.png')
    model = {'source_image':'source.png','title':'</script><script>alert(1)</script>',
             'entities':[], 'issues':['Need scale']}
    engine.dump(tmp_path / 'model.json', model)
    result = review.preview(tmp_path / 'model.json', tmp_path / 'preview')
    assert result['state'] == 'DRAFT_NOT_VALIDATED' and result['warnings']
    html = (tmp_path / 'preview/review.html').read_text(encoding='utf-8')
    assert '</script><script>alert(1)' not in html and '\\u003c/script>' in html
    assert 'data:image/png;base64,' in html
    assert (tmp_path / 'preview/session.zip').is_file()


def test_pdf_vector_export_preserves_cubic_control_points(tmp_path):
    import pymupdf
    import ezdxf
    source = tmp_path / 'vectors.pdf'
    with pymupdf.open() as doc:
        page = doc.new_page(width=300, height=200)
        page.draw_line((10,20),(110,20))
        shape = page.new_shape(); shape.draw_bezier((10,30),(20,40),(30,50),(40,30)); shape.finish(closePath=False); shape.commit()
        page.insert_text((10,180),'Uncalibrated graphic fixture')
        doc.save(source)
    result = pdf_vectors.extract(source, tmp_path / 'vectors')
    cad = ezdxf.readfile(tmp_path / 'vectors/pdf-strokes-UNCALIBRATED.dxf')
    line, spline = list(cad.modelspace())
    assert cad.units == 0 and line.dxf.start.x == 10 and line.dxf.start.y == -20
    assert list(map(tuple,spline.control_points)) == [(10,-30,0),(20,-40,0),(30,-50,0),(40,-30,0)]
    assert result['state'] == 'UNCALIBRATED_GRAPHICS_NOT_NOMINAL_CAD' and result['text_blocks'] == 1
    assert result['audit_errors'] == 0


def test_benchmark_detects_position_error_and_not_only_lengths(tmp_path):
    import ezdxf
    def write(name, shift):
        doc=ezdxf.new(); doc.units=4
        doc.modelspace().add_line((shift,0),(100+shift,0))
        doc.modelspace().add_circle((25,25),10)
        path=tmp_path/name; doc.saveas(path); return path
    reference=write('reference.dxf',0)
    assert benchmark.compare(reference,write('same.dxf',0),'mm',0.02)['pass']
    assert not benchmark.compare(reference,write('shifted.dxf',1),'mm',0.02)['pass']


def test_benchmark_matches_ambiguous_neighbours_bijectively(tmp_path):
    import ezdxf
    def write(name, xs):
        doc=ezdxf.new(); doc.units=4
        for x in xs: doc.modelspace().add_line((x,0),(x,10))
        path=tmp_path/name; doc.saveas(path); return path
    result=benchmark.compare(write('reference.dxf',[0,0.9]),write('candidate.dxf',[0.1,-0.9]),'mm',1)
    assert result['pass'] and result['matched_entities']==2


def test_modified_session_source_fails_checksum(tmp_path):
    source=tmp_path/'source.txt';source.write_text('original synthetic definition')
    model=tmp_path/'model.json';engine.dump(model,{'sources':[{'path':source.name}]})
    checkpoint=tmp_path/'session.zip';recovery.checkpoint(model,checkpoint)
    tampered=tmp_path/'tampered.zip'
    with zipfile.ZipFile(checkpoint) as original,zipfile.ZipFile(tampered,'w') as modified:
        for name in original.namelist():
            modified.writestr(name,b'modified' if name.startswith('sources/') else original.read(name))
    with pytest.raises(ValueError,match='checksum'):
        recovery.resume(tampered,tmp_path/'restored')
    assert not (tmp_path/'restored').exists()


def test_pdf_disconnected_subpaths_are_not_joined(tmp_path):
    import pymupdf,ezdxf
    source=tmp_path/'paths.pdf'
    with pymupdf.open() as doc:
        page=doc.new_page(width=300,height=200);shape=page.new_shape()
        shape.draw_line((10,10),(20,10));shape.draw_line((100,100),(120,100))
        shape.finish(closePath=True);shape.commit();doc.save(source)
    pdf_vectors.extract(source,tmp_path/'vectors')
    cad=ezdxf.readfile(tmp_path/'vectors/pdf-strokes-UNCALIBRATED.dxf')
    assert all(abs(e.dxf.start.y-e.dxf.end.y)<1e-9 for e in cad.modelspace())
