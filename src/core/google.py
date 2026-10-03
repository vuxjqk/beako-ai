from dataclasses import dataclass

import jwt

from src.core import config

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")

# Caches Google's public keys (they rotate roughly daily) instead of fetching per request
_jwk_client = jwt.PyJWKClient(GOOGLE_JWKS_URL, cache_keys=True, lifespan=3600, timeout=10)


class GoogleTokenError(Exception):
    pass


@dataclass(frozen=True)
class GoogleProfile:
    sub: str
    email: str
    name: str | None
    picture: str | None


def verify_google_id_token(token: str) -> GoogleProfile:
    if not config.GOOGLE_CLIENT_IDS:
        raise GoogleTokenError("Google login is not configured")
    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=config.GOOGLE_CLIENT_IDS,
            issuer=GOOGLE_ISSUERS,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as e:
        raise GoogleTokenError(str(e)) from e

    email = claims.get("email")
    # Accounts are linked by email, so it must be one Google has verified
    if not email or claims.get("email_verified") is not True:
        raise GoogleTokenError("Google account email is not verified")

    return GoogleProfile(
        sub=claims["sub"],
        email=email.lower(),
        name=claims.get("name"),
        picture=claims.get("picture"),
    )
