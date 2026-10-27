"""Only direct, bounded downloads from operator-approved attachment hosts."""
import ipaddress
from pathlib import Path
import socket
from urllib.parse import urlsplit
import httpx

EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp', '.bmp'}
MIME_EXTENSIONS = {'application/pdf': '.pdf', 'image/png': '.png', 'image/jpeg': '.jpg',
                   'image/tiff': '.tiff', 'image/webp': '.webp', 'image/bmp': '.bmp'}


def validate_url(url, hosts):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in hosts or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError('Only HTTPS attachments from approved hosts are accepted; no redirects')
    return parsed.hostname


def public_dns(host):
    addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError('Attachment host must resolve exclusively to public addresses')


async def download(file, destination, settings, client=None):
    import anyio
    host = validate_url(file['download_url'], settings.file_hosts)
    await anyio.to_thread.run_sync(public_dns, host, abandon_on_cancel=True)
    if not file.get('file_id'):
        raise ValueError('A ChatGPT file reference is required')
    extension = Path(file.get('file_name') or '').suffix.lower()
    extension = extension if extension in EXTENSIONS else MIME_EXTENSIONS.get(file.get('mime_type'))
    if extension not in EXTENSIONS:
        raise ValueError('Upload a PDF or supported PNG/JPEG/TIFF/WebP/BMP image')
    target = Path(destination) / ('source' + extension)
    owned = client is None
    client = client or httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=False)
    try:
        async with client.stream('GET', file['download_url'], follow_redirects=False) as response:
            if response.status_code != 200:
                raise ValueError('Attachment download failed; attach the file again to renew access')
            length = response.headers.get('content-length')
            if length and int(length) > settings.max_upload_bytes:
                raise ValueError('File exceeds the upload limit for this deployment')
            size = 0
            with target.open('xb') as out:
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        raise ValueError('File exceeds the upload limit')
                    out.write(chunk)
            if size == 0:
                raise ValueError('Empty attachment')
        return target
    finally:
        if owned:
            await client.aclose()
