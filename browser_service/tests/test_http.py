import json
from dataclasses import replace
import time
from urllib.parse import urlsplit
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from engcad_web.app import create_app
from engcad_web.tools import FILE_SCHEMA
ROOT = Path(__file__).resolve().parents[2]

HEADERS = {'Authorization': 'Bearer alice', 'Accept': 'application/json, text/event-stream',
           'MCP-Protocol-Version': '2026-07-28'}


def rpc(client, method, params=None, token='alice'):
    params = {**(params or {}), '_meta': {'io.modelcontextprotocol/protocolVersion':'2026-07-28',
                                       'io.modelcontextprotocol/clientCapabilities':{}}}
    response = client.post('/mcp', json={'jsonrpc':'2.0','id':1,'method':method,'params':params},
                           headers={**HEADERS, 'Authorization':'Bearer '+token, 'MCP-Method':method,
                                    **({'MCP-Name':params['name']} if 'name' in params else {})})
    assert response.status_code == 200, response.text
    body = response.json()
    assert 'error' not in body, body
    return body['result']


def call(client, name, args=None, token='alice'):
    return rpc(client, 'tools/call', {'name':name, 'arguments':args or {}}, token)


def complete(client, identifier):
    for _ in range(160):
        result = call(client, 'get_cad_job', {'job_id':identifier})['structuredContent']
        if result['status'] not in ('queued','running'):
            return result
        time.sleep(1)
    raise AssertionError('Job did not finish')


def test_health_auth_and_discovery(settings, verifier):
    with TestClient(create_app(settings, verifier), base_url=settings.base_url) as client:
        assert client.get('/health').json()['status'] == 'ok'
        assert client.get('/').status_code == 200
        response = client.post('/mcp', json={})
        assert response.status_code == 401
        assert 'oauth-protected-resource' in response.headers['www-authenticate']
        metadata = client.get('/.well-known/oauth-protected-resource/mcp').json()
        assert metadata['resource'] == settings.resource
        assert metadata['authorization_servers'] == [settings.issuer]
        discovered = rpc(client, 'server/discover', {'supportedVersions':['2026-07-28'], 'capabilities':{}})
        assert '2026-07-28' in discovered['supportedVersions']
        tools = rpc(client, 'tools/list')['tools']
        assert len(tools) == 6
        inspector = next(tool for tool in tools if tool['name'] == 'inspect_cad_source')
        assert inspector['_meta']['openai/fileParams'] == ['file']
        assert inspector['inputSchema']['properties']['file'] == FILE_SCHEMA
        guide = call(client, 'get_cad_model_guide')
        assert 'comparison_tolerance' in guide['structuredContent']['guide']


def test_bad_token_and_insufficient_scope(settings, verifier, local_attachment):
    with TestClient(create_app(settings, verifier), base_url=settings.base_url) as client:
        response = client.post('/mcp', json={}, headers={**HEADERS, 'Authorization':'Bearer bad'})
        assert response.status_code == 401
        result = call(client, 'inspect_cad_source', {'file':local_attachment}, token='readonly')
        assert result['isError'] is True
        assert 'mcp/www_authenticate' in result['_meta']


@pytest.mark.parametrize('profile',['full','free'])
def test_http_end_to_end_dxf_and_download(settings, verifier, local_attachment,profile):
    settings=replace(settings,profile=profile)
    app = create_app(settings, verifier)
    with TestClient(app, base_url=settings.base_url) as client:
        submitted = call(client,'inspect_cad_source',{'file':local_attachment})['structuredContent']
        inspection = complete(client, submitted['job_id'])
        assert inspection['status'] == 'complete', inspection
        page = call(client, 'read_cad_page', {'job_id':inspection['id'], 'page':1})
        assert page['content'][1]['type'] == 'image'
        assert page['structuredContent']['pixel_size'] == [800,500]
        denied = call(client, 'get_cad_job', {'job_id':inspection['id']}, token='bob')
        assert denied['isError']
        model = json.loads((ROOT/'examples/nominal/model.json').read_text(encoding='utf-8'))
        # These paths must be replaced by the backend, never opened.
        model['source_image'] = '/etc/passwd'
        model['engineering']['sources'][0]['path'] = '../../private.pdf'
        exported = call(client,'export_cad_dxf',{'inspection_id':inspection['id'],'page':1,'model':model})['structuredContent']
        result = complete(client,exported['job_id'])
        assert result['status'] == 'complete', result
        assert result['state'] == 'DEFINED_REVIEW_PENDING'
        link = result['artifacts']['plano.dxf']
        download = client.get(link)
        assert download.status_code == 200
        assert b'ENTITIES' in download.content
        assert download.headers['cache-control'] == 'private, no-store'
        assert 'attachment' in download.headers['content-disposition']
        tampered = client.get(link.replace('plano.dxf','informe.json'))
        assert tampered.status_code == 410
        model['calibration']['status'] = 'unscaled'
        bad = call(client,'export_cad_dxf',{'inspection_id':inspection['id'],'page':1,'model':model})['structuredContent']
        blocked = complete(client,bad['job_id'])
        assert blocked['status'] == 'blocked', blocked
        assert 'artifacts' not in blocked
        step_source = call(client,'inspect_cad_source',{'file':{**local_attachment,'file_id':'step_fixture','file_name':'spec.pdf','mime_type':'application/pdf'}})['structuredContent']
        step_inspection = complete(client,step_source['job_id'])
        assert step_inspection['status'] == 'complete'
        step = json.loads((ROOT/'examples/step/model-step.json').read_text(encoding='utf-8'))
        submitted_step = call(client,'export_cad_step',{'inspection_id':step_inspection['id'],'page':1,'model':step})['structuredContent']
        step_result = complete(client,submitted_step['job_id'])
        assert step_result['status'] == 'complete', step_result
        assert step_result['result']['properties_match']
        assert client.get(step_result['artifacts']['pieza.step']).status_code == 200


def test_invalid_file_host_and_bad_page(settings, verifier, local_attachment):
    with TestClient(create_app(settings, verifier), base_url=settings.base_url) as client:
        local_attachment['download_url'] = 'http://127.0.0.1/private'
        result = call(client,'inspect_cad_source',{'file':local_attachment})
        assert result['isError']
        result = call(client,'read_cad_page',{'job_id':'0'*32,'page':1})
        assert result['isError']


def test_wrong_host_rejected(settings, verifier):
    with TestClient(create_app(settings, verifier), base_url=settings.base_url) as client:
        response = client.post('/mcp', headers={**HEADERS,'Host':'attacker.test'}, json={'jsonrpc':'2.0','id':1,'method':'tools/list'})
        assert response.status_code == 421
