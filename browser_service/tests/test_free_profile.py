from dataclasses import replace
import json
from pathlib import Path
import pytest
import yaml
from PIL import Image
from engcad_web.config import Settings
from engcad_web.worker import preflight


def test_free_profile_clamps_limits(settings):
    free=replace(settings,profile='free')
    assert free.max_upload_bytes==5*1024*1024
    assert free.retention_seconds==3600
    assert free.max_queue==2
    assert free.max_user_jobs==6
    assert free.parser_limits['pages']==4
    assert free.parser_limits['page_pixels']==2_000_000


def test_env_defaults_to_free(settings,monkeypatch):
    for key,value in {'CAD_BASE_URL':settings.base_url,'CAD_OAUTH_ISSUER':settings.issuer,
                      'CAD_JWKS_URL':settings.jwks_url,'CAD_SIGNING_KEY':settings.signing_key}.items():
        monkeypatch.setenv(key,value)
    monkeypatch.delenv('CAD_PROFILE',raising=False)
    assert Settings.from_env().profile=='free'
    assert Settings.from_env().max_upload_bytes==5*1024*1024


@pytest.mark.parametrize('explicit',[False,True])
def test_render_provided_url_is_used_only_without_explicit_origin(settings,monkeypatch,explicit):
    monkeypatch.setenv('CAD_OAUTH_ISSUER',settings.issuer)
    monkeypatch.setenv('CAD_JWKS_URL',settings.jwks_url)
    monkeypatch.setenv('CAD_SIGNING_KEY',settings.signing_key)
    monkeypatch.setenv('RENDER_EXTERNAL_URL','https://cad-test.onrender.com')
    monkeypatch.delenv('CAD_BASE_URL',raising=False)
    if explicit:
        monkeypatch.setenv('CAD_BASE_URL',settings.base_url)
    config=Settings.from_env()
    assert config.base_url==(settings.base_url if explicit else 'https://cad-test.onrender.com')


def test_free_rejects_too_many_pdf_pages(settings,tmp_path):
    import pymupdf
    target=tmp_path/'five.pdf'
    doc=pymupdf.open()
    for _ in range(5):
        doc.new_page()
    doc.save(target);doc.close()
    with pytest.raises(ValueError,match='1-4'):
        preflight(target,replace(settings,profile='free').parser_limits)


def test_free_rejects_large_image(settings,tmp_path):
    target=tmp_path/'large.png'
    Image.new('RGB',(2100,2000),'white').save(target)
    with pytest.raises(ValueError):
        preflight(target,replace(settings,profile='free').parser_limits)


def test_deployment_has_no_paid_resources():
    root=Path(__file__).resolve().parents[2]
    service=yaml.safe_load((root/'browser_service/deploy/render.yaml').read_text())['services'][0]
    assert service['plan']=='free'
    assert 'disk' not in service
    assert service['numInstances']==1
    assert service['autoDeployTrigger']=='off'
    assert next(e['value'] for e in service['envVars'] if e['key']=='CAD_PROFILE')=='free'
