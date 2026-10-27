from pathlib import Path
import shutil
import time
import pytest
from mcp.server.auth.provider import AccessToken
from engcad_web.config import Settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def settings(tmp_path):
    return Settings(base_url='https://cad.example.test', issuer='https://identity.example.test/',
                    jwks_url='https://identity.example.test/keys', signing_key='synthetic-test-key-'*3,
                    data_dir=tmp_path / 'jobs').validate()


class TestVerifier:
    __test__ = False
    def __init__(self, settings):
        self.settings = settings

    async def verify_token(self, token):
        if token not in ('alice', 'bob', 'readonly'):
            return None
        return AccessToken(token=token, client_id='test-client', subject=token,
                           scopes=['cad:read'] if token == 'readonly' else ['cad:read', 'cad:write'],
                           resource=self.settings.resource, expires_at=int(time.time())+3600)


@pytest.fixture
def verifier(settings):
    return TestVerifier(settings)


@pytest.fixture
def local_attachment(monkeypatch):
    async def fake_download(file, root, settings):
        if file['file_id'] == 'step_fixture':
            import pymupdf
            path = root / 'source.pdf'
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((40,80),'Synthetic nominal prism: width 20 mm, height 10 mm, depth 5 mm. No other features.')
            page.insert_text((40,110),'Profile centered XY. Bottom Z=0, extrusion +Z. Physical accuracy unknown.')
            doc.save(path)
            doc.close()
            return path
        path = root / 'source.png'
        shutil.copy2(ROOT / 'examples' / 'nominal' / 'fixture.png', path)
        return path
    monkeypatch.setattr('engcad_web.files.download', fake_download)
    return {'download_url': 'https://files.openai.com/synthetic-only', 'file_id': 'fixture',
            'file_name': 'fixture.png', 'mime_type': 'image/png'}
