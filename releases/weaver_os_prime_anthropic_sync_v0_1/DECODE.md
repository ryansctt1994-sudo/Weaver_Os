# Decode Instructions

The ZIP packages are stored as `.zip.b64` files because this connector push path writes UTF-8 text files.

Decode all packages:

```bash
cd releases/weaver_os_prime_anthropic_sync_v0_1
for f in packages/*.zip.b64; do base64 -d "$f" > "${f%.b64}"; done
```

Verify checksums using `MANIFEST.json`.

Boundary: decoding packages does not grant authority, promotion, E4 status, production approval, or deployment approval.
