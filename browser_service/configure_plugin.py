"""Generate a remote plugin only after a real HTTPS service URL is available."""
import argparse
import json
from pathlib import Path
import shutil
from urllib.parse import urlsplit
import zipfile


def configure(base_url, publisher, output, client_id=None):
    base_url = base_url.rstrip('/')
    parsed = urlsplit(base_url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query
            or parsed.fragment or parsed.path or parsed.hostname in {'localhost', '127.0.0.1'}
            or parsed.hostname.endswith(('.example', '.test', '.invalid')) or 'YOUR-' in base_url.upper()):
        raise ValueError('Supply the actual deployed HTTPS origin, without a path or placeholder hostname')
    if not publisher.strip():
        raise ValueError('Supply the actual publishing identity')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(Path(__file__).parent / 'plugin' / 'skills', output / 'skills')
    manifest = {'$schema':'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json',
        'name':'engineering-cad-converter-web','version':'1.0.0','description':'CAD conversion from ChatGPT attachments with evidence and engineering checks.',
        'license':'MIT','extensions':{'com.openai':{'interface':{
            'displayName':'Engineering CAD Converter Web','developerName':publisher,
            'shortDescription':'Planos a CAD desde ChatGPT con medidas trazables',
            'longDescription':'Receives PDF and image attachments, preserves evidence, checks dimensions and exports DXF or supported STEP. Requires technical review.',
            'category':'Productivity','websiteURL':base_url,'privacyPolicyURL':base_url+'/privacy',
            'termsOfServiceURL':base_url+'/terms','supportURL':base_url+'/support',
            'defaultPrompt':['Convierte este plano a DXF. Comprueba las unidades, la escala y las cotas antes de exportar.']}}}}
    client = {'mode':'provided','clientId':client_id,'tokenEndpointAuthMethod':'none'} if client_id else {'mode':'cimd'}
    mcp = {'$schema':'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json','mcpServers':{'cad':{
        'type':'streamable-http','url':base_url+'/mcp','extensions':{'com.openai':{'auth':{
            'type':'oauth','client':client,'resource':base_url+'/mcp','baseScopes':['cad:read','cad:write']}}}}}}
    for name, content in [('plugin.json',manifest),('mcp.json',mcp)]:
        (output/name).write_text(json.dumps(content,ensure_ascii=False,indent=2),encoding='utf-8')
    archive = output.parent / (output.name + '.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(output.rglob('*')):
            if path.is_file():
                z.write(path,path.relative_to(output).as_posix())
    return archive


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url',required=True)
    p.add_argument('--publisher',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--oauth-client-id')
    a = p.parse_args()
    print(configure(a.base_url,a.publisher,a.output,a.oauth_client_id))
