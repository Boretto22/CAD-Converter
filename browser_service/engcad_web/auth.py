"""Resource server only: an external OAuth provider signs users in."""
import hashlib
import jwt
import anyio
from mcp.server.auth.provider import AccessToken


class JWTVerifier:
    def __init__(self, settings):
        self.settings = settings
        self.keys = jwt.PyJWKClient(settings.jwks_url, cache_keys=True, lifespan=300, timeout=10)

    def decode(self, token):
        key = self.keys.get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=['RS256'], issuer=self.settings.issuer,
                            audience=self.settings.resource,
                            options={'require': ['exp', 'iat', 'sub', 'iss', 'aud']})
        if not isinstance(claims['sub'], str) or not claims['sub']:
            raise jwt.InvalidTokenError('Missing subject')
        scopes = claims.get('scope', '').split()
        return AccessToken(token=token, client_id=claims.get('azp', claims.get('client_id', 'oauth-client')),
                           subject=claims['sub'], scopes=scopes, expires_at=int(claims['exp']),
                           resource=self.settings.resource)

    async def verify_token(self, token):
        try:
            return await anyio.to_thread.run_sync(self.decode, token)
        except (jwt.PyJWTError, ValueError, TypeError, OSError):
            return None


def owner_key(settings, token):
    if not token or not token.subject:
        raise PermissionError('Authenticated user required')
    return hashlib.sha256((settings.issuer + '\0' + token.subject).encode()).hexdigest()
