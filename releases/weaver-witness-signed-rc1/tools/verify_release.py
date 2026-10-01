#!/usr/bin/env python3
"""Verify a detached Ed25519 signature and every pinned payload byte."""
import base64
import hashlib
import json
import pathlib
import sys
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

root = pathlib.Path(__file__).resolve().parents[1]
manifest_bytes = (root / 'MANIFEST.json').read_bytes()
signature = base64.b64decode((root / 'MANIFEST.sig').read_text().strip(), validate=True)
public = base64.b64decode((root / 'PUBLIC_KEY.b64').read_text().strip(), validate=True)
Ed25519PublicKey.from_public_bytes(public).verify(signature, manifest_bytes)
manifest = json.loads(manifest_bytes)
expected = manifest['files']
actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()
          and '__pycache__' not in p.parts}
allowed = set(expected) | {'MANIFEST.json', 'MANIFEST.sig', 'PUBLIC_KEY.b64', 'tools/verify_release.py'}
if actual != allowed:
    raise SystemExit(f'FILE SET MISMATCH missing={sorted(allowed-actual)} extra={sorted(actual-allowed)}')
for name, digest in expected.items():
    if name.startswith('/') or '..' in pathlib.PurePosixPath(name).parts:
        raise SystemExit('UNSAFE PATH')
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
        raise SystemExit(f'HASH MISMATCH: {name}')
print('SIGNATURE AND FILE MANIFEST: PASS')
print('PUBLIC KEY SHA256:', hashlib.sha256(public).hexdigest())
print('MANIFEST SHA256:', hashlib.sha256(manifest_bytes).hexdigest())
