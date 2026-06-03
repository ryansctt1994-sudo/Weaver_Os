from __future__ import annotations

import json

import jwt
from jwt import PyJWKClient

from .utils import b64url_decode, fail, read_text_arg

EXPECTED = {
    "repository": "ryansctt1994-sudo/Weaver_Os",
    "workflow_file": ".github/workflows/release.yml",
    "environment": "pypi",
    "issuer": "https://token.actions.githubusercontent.com",
    "audience": "pypi",
    "jwks_url": "https://token.actions.githubusercontent.com/.well-known/jwks",
}


def decode_jwt_unverified(token: str) -> tuple[dict, dict]:
    parts = token.strip().split(".")
    if len(parts) != 3:
        fail("Invalid JWT format")
    header = json.loads(b64url_decode(parts[0]).decode("utf-8"))
    payload = json.loads(b64url_decode(parts[1]).decode("utf-8"))
    return header, payload


def verify_oidc_token(token_or_path: str) -> dict:
    token = read_text_arg(token_or_path)
    header, _ = decode_jwt_unverified(token)

    alg = header.get("alg")
    if alg not in {"RS256", "ES256"}:
        fail(f"Unexpected JWT alg: {alg}")

    jwks_client = PyJWKClient(EXPECTED["jwks_url"])
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=[alg],
        audience=EXPECTED["audience"],
        issuer=EXPECTED["issuer"],
        options={"require": ["exp", "iat", "iss", "aud", "sub"]},
    )

    if claims.get("repository") != EXPECTED["repository"]:
        fail(f"Repository mismatch: {claims.get('repository')}")

    jwfr = claims.get("job_workflow_ref") or ""
    expected_prefix = f"{EXPECTED['repository']}/{EXPECTED['workflow_file']}@"
    if not jwfr.startswith(expected_prefix):
        fail(f"job_workflow_ref mismatch: {jwfr}")

    if claims.get("environment") and claims["environment"] != EXPECTED["environment"]:
        fail(f"Environment mismatch: {claims['environment']}")

    return claims
