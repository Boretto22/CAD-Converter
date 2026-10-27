from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
import os


@dataclass(frozen=True)
class Settings:
    base_url: str
    issuer: str
    jwks_url: str
    signing_key: str
    data_dir: Path
    retention_seconds: int = 86400
    link_seconds: int = 600
    max_upload_bytes: int = 20 * 1024 * 1024
    worker_timeout: int = 120
    max_user_jobs: int = 20
    max_total_jobs: int = 200
    max_queue: int = 6
    file_hosts: tuple[str, ...] = ('files.openai.com', 'files.oaiusercontent.com')
    profile: str = 'full'

    def __post_init__(self):
        if self.profile == 'free':
            for name, limit in {'retention_seconds':3600, 'max_upload_bytes':5*1024*1024,
                                'max_user_jobs':6, 'max_total_jobs':24, 'max_queue':2}.items():
                object.__setattr__(self, name, min(getattr(self, name), limit))

    @property
    def parser_limits(self):
        return ({'pages':4, 'page_pixels':2_000_000, 'total_pixels':6_000_000, 'source_pixels':4_000_000}
                if self.profile == 'free' else
                {'pages':12, 'page_pixels':25_000_000, 'total_pixels':35_000_000, 'source_pixels':25_000_000})

    @property
    def resource(self):
        return self.base_url.rstrip('/') + '/mcp'

    def validate(self):
        if self.profile not in {'free','full'}:
            raise ValueError('CAD_PROFILE must be free or full')
        for name, value in [('base_url', self.base_url), ('issuer', self.issuer), ('jwks_url', self.jwks_url)]:
            url = urlsplit(value)
            if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError(f'{name} must be an absolute HTTPS URL without credentials, query or fragment')
        if urlsplit(self.base_url).path not in ('', '/'):
            raise ValueError('base_url must be the origin; /mcp is added by the service')
        if urlsplit(self.jwks_url).hostname != urlsplit(self.issuer).hostname:
            raise ValueError('JWKS must belong to the configured trusted issuer host')
        if len(self.signing_key.encode()) < 32:
            raise ValueError('CAD_SIGNING_KEY must contain at least 32 bytes')
        if any(marker in self.signing_key.upper() for marker in ('GENERATE-A-', 'CHANGE-ME', 'YOUR-SECRET', 'PLACEHOLDER')):
            raise ValueError('Replace the example signing key with a newly generated random secret')
        if not 60 <= self.link_seconds <= 3600 or not self.link_seconds <= self.retention_seconds <= 86400:
            raise ValueError('Links must last 1-60 minutes; retained jobs at most 24 hours')
        if not self.file_hosts or any('*' in h or '/' in h or ':' in h for h in self.file_hosts):
            raise ValueError('File hosts must be explicit DNS hostnames, without wildcards')
        return self

    @classmethod
    def from_env(cls):
        base_url = os.environ.get('CAD_BASE_URL') or os.environ.get('RENDER_EXTERNAL_URL')
        required = ('CAD_OAUTH_ISSUER', 'CAD_JWKS_URL', 'CAD_SIGNING_KEY')
        missing = [key for key in required if not os.environ.get(key)]
        if not base_url:
            missing.insert(0, 'CAD_BASE_URL (or Render RENDER_EXTERNAL_URL)')
        if missing:
            raise ValueError('Missing configuration: ' + ', '.join(missing))
        return cls(base_url=base_url.rstrip('/'), issuer=os.environ['CAD_OAUTH_ISSUER'],
                   jwks_url=os.environ['CAD_JWKS_URL'], signing_key=os.environ['CAD_SIGNING_KEY'],
                   data_dir=Path(os.environ.get('CAD_DATA_DIR', '/tmp/engcad/jobs')),
                   profile=os.environ.get('CAD_PROFILE', 'free'),
                   file_hosts=tuple(x.strip().lower() for x in os.environ.get('CAD_FILE_HOSTS',
                       'files.openai.com,files.oaiusercontent.com').split(',') if x.strip())).validate()
