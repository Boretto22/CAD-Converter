import asyncio
from dataclasses import replace
import hashlib
import json
import time
from types import SimpleNamespace
import pytest
import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from engcad_web.auth import JWTVerifier
from engcad_web.files import validate_url, download
from engcad_web.store import Store


@pytest.mark.parametrize('url', ['http://files.openai.com/x', 'https://127.0.0.1/x', 'https://files.openai.com.evil.test/x',
    'https://files.openai.com@evil.test/x', 'https://user:pass@files.openai.com/x',
    'https://files.openai.com:8443/x', 'https://files.openai.com/x#fragment'])
def test_attachment_url_rejected(settings,url):
    with pytest.raises(ValueError):
        validate_url(url,settings.file_hosts)


def test_jwt_signature_audience_expiry_issuer(settings):
    key = rsa.generate_private_key(public_exponent=65537,key_size=2048)
    other = rsa.generate_private_key(public_exponent=65537,key_size=2048)
    verifier = JWTVerifier(settings)
    verifier.keys.get_signing_key_from_jwt = lambda token: SimpleNamespace(key=key.public_key())
    claims = {'iss':settings.issuer,'aud':settings.resource,'sub':'alice','iat':int(time.time()),'exp':int(time.time())+100,'scope':'cad:read cad:write'}
    valid = jwt.encode(claims,key,algorithm='RS256')
    assert asyncio.run(verifier.verify_token(valid)).subject == 'alice'
    for change in ({'aud':'another-resource'},{'iss':'https://other.test/'},{'exp':int(time.time())-1},{'sub':''}):
        assert asyncio.run(verifier.verify_token(jwt.encode({**claims,**change},key,algorithm='RS256'))) is None
    assert asyncio.run(verifier.verify_token(jwt.encode(claims,other,algorithm='RS256'))) is None


def test_attachment_rejection_diagnostic_excludes_signed_capability(settings):
    with pytest.raises(ValueError) as error:
        validate_url('https://files02.oaiusercontent.com/private-plan.pdf?sig=DO-NOT-SHOW',settings.file_hosts)
    assert 'files02.oaiusercontent.com' in str(error.value)
    assert 'private-plan' not in str(error.value)
    assert 'DO-NOT-SHOW' not in str(error.value)


def test_store_expiry_ownership_tampering_and_cleanup(settings):
    store = Store(settings)
    job = store.create('alice','dxf')
    store.update(job,'complete')
    with pytest.raises(ValueError):
        store.get(job,'bob')
    expiry = int(time.time())+60
    signature = store.signature(job,'plano.dxf',expiry)
    store.authorize_download(job,'plano.dxf',expiry,signature)
    with pytest.raises(ValueError):
        store.authorize_download(job,'pieza.step',expiry,signature)
    with pytest.raises(ValueError):
        store.authorize_download(job,'plano.dxf',int(time.time())-1,signature)
    with store.connect() as db:
        db.execute('UPDATE jobs SET expires=? WHERE id=?',(time.time()-1,job))
    with pytest.raises(ValueError):
        store.get(job,'alice')
    assert store.prune() == 1
    assert not store.directory(job).exists()
    with pytest.raises(ValueError):
        store.directory('../outside')


def test_store_queue_and_restart(settings):
    store = Store(replace(settings,max_queue=1))
    job = store.create('alice','inspect')
    with pytest.raises(ValueError):
        store.create('bob','inspect')
    restarted = Store(settings)
    assert restarted.get(job,'alice')['status'] == 'failed'


@pytest.mark.parametrize('status,size',[(302,10),(200,0),(200,100)])
def test_download_redirect_size_empty(settings,tmp_path,monkeypatch,status,size):
    monkeypatch.setattr('engcad_web.files.public_dns',lambda host:None)
    settings=replace(settings,max_upload_bytes=20)
    async def exercise():
        transport=httpx.MockTransport(lambda request:httpx.Response(status,content=b'x'*size))
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(ValueError):
                await download({'download_url':'https://files.openai.com/f','file_id':'f','file_name':'x.png'},tmp_path,settings,client)
    asyncio.run(exercise())


def test_private_dns_rejected(monkeypatch):
    from engcad_web.files import public_dns
    monkeypatch.setattr('socket.getaddrinfo',lambda *a,**k:[(None,None,None,None,('127.0.0.1',443))])
    with pytest.raises(ValueError):
        public_dns('files.openai.com')


@pytest.mark.parametrize('change',[{'base_url':'http://insecure.test'},{'issuer':'https://user:pass@identity.example.test'},
    {'jwks_url':'https://attacker.test/key'},{'signing_key':'short'},{'file_hosts':('*',)}])
def test_bad_production_config(settings,change):
    with pytest.raises(ValueError):
        replace(settings,**change).validate()


def test_example_secret_is_not_usable(settings):
    with pytest.raises(ValueError):
        replace(settings,signing_key='GENERATE-A-NEW-RANDOM-SECRET-OF-AT-LEAST-32-BYTES').validate()


def test_storage_reserve(settings,monkeypatch):
    store=Store(settings)
    monkeypatch.setattr('engcad_web.store.shutil.disk_usage',lambda path:SimpleNamespace(free=0))
    with pytest.raises(ValueError):
        store.create('alice','inspect')


def test_attachment_wall_timeout(settings,monkeypatch):
    from engcad_web.manager import Manager
    original_wait=asyncio.wait_for
    async def quick_wait(awaitable,timeout):
        return await original_wait(awaitable,timeout=0.01)
    async def slow_download(*args):
        await asyncio.sleep(1)
    monkeypatch.setattr('engcad_web.manager.asyncio.wait_for',quick_wait)
    monkeypatch.setattr('engcad_web.manager.files.download',slow_download)
    async def exercise():
        manager=Manager(settings)
        identifier=manager.store.create('alice','inspect')
        await manager.run(identifier,'inspect',{'file_id':'slow'})
        assert manager.store.get(identifier,'alice')['status']=='failed'
        assert 'time limit' in manager.store.get(identifier,'alice')['error']
        await manager.close()
    asyncio.run(exercise())
