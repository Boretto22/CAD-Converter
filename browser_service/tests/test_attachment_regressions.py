import asyncio
import httpx
import pytest
from engcad_web.files import download
from engcad_web.manager import Manager


def test_attachment_without_optional_metadata(settings, tmp_path, monkeypatch):
    monkeypatch.setattr('engcad_web.files.public_dns', lambda host: None)
    # The resolver is mocked; run it inline without a test-only worker thread.
    async def inline(function, *args, **kwargs):
        return function(*args)
    monkeypatch.setattr('anyio.to_thread.run_sync', inline)
    async def exercise():
        transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b'png-fixture', headers={'Content-Type': 'image/png; charset=binary'}))
        async with httpx.AsyncClient(transport=transport) as client:
            path = await download({'download_url': 'https://files.openai.com/f', 'file_id': 'f'}, tmp_path, settings, client)
            assert path.suffix == '.png'
            assert path.read_bytes() == b'png-fixture'
    asyncio.run(exercise())


def test_download_validation_reason_survives_job(settings, monkeypatch):
    async def rejected(*args):
        raise ValueError('File exceeds the upload limit for this deployment')
    monkeypatch.setattr('engcad_web.manager.files.download', rejected)
    async def exercise():
        manager = Manager(settings)
        identifier = manager.store.create('alice', 'inspect')
        await manager.run(identifier, 'inspect', {'file_id': 'f'})
        job = manager.store.get(identifier, 'alice')
        assert job['status'] == 'blocked'
        assert 'upload limit' in job['error']
        await manager.close()
    asyncio.run(exercise())


def test_dxf_evidence_must_match_selected_page(settings, monkeypatch):
    async def exercise():
        manager = Manager(settings)
        monkeypatch.setattr(manager, 'page', lambda *args: ({}, settings.data_dir / 'review.png'))
        model = {'engineering': {'evidence': [{'id': 'D1', 'source_id': 'S1', 'page': 2}]}}
        with pytest.raises(ValueError, match='page'):
            await manager.submit_build('alice', '0'*32, 1, model, 'dxf')
        with manager.store.connect() as db:
            assert db.execute('SELECT count(*) FROM jobs').fetchone()[0] == 0
        await manager.close()
    asyncio.run(exercise())
