"""Verify the frozen witness ZIP against a separately supplied key fingerprint."""

import argparse
import base64
import hashlib
import io
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def verify_archive_bytes(raw: bytes, expected_fingerprint: str) -> dict[str, str]:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_fingerprint):
        raise ValueError("expected fingerprint must be 64 lowercase hex characters")

    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate ZIP entry")
        for info in bundle.infolist():
            path = PurePosixPath(info.filename)
            mode = info.external_attr >> 16
            if (
                not info.filename
                or info.filename.startswith("/")
                or "\\" in info.filename
                or any(part in (".", "..") for part in info.filename.split("/"))
                or info.is_dir()
                or (mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG))
                or str(path) != info.filename
            ):
                raise ValueError(f"unsafe ZIP entry: {info.filename}")

        required = {"MANIFEST.json", "MANIFEST.sig", "PUBLIC_KEY.b64"}
        if not required.issubset(names):
            raise ValueError("missing signature material")
        public = base64.b64decode(bundle.read("PUBLIC_KEY.b64").strip(), validate=True)
        fingerprint = hashlib.sha256(public).hexdigest()
        if fingerprint != expected_fingerprint:
            raise ValueError("public key fingerprint mismatch")

        manifest_bytes = bundle.read("MANIFEST.json")
        signature = base64.b64decode(bundle.read("MANIFEST.sig").strip(), validate=True)
        Ed25519PublicKey.from_public_bytes(public).verify(signature, manifest_bytes)
        manifest = json.loads(manifest_bytes)
        if manifest.get("schema") != "weaver-witness-release-1":
            raise ValueError("unknown manifest schema")
        files = manifest.get("files")
        if not isinstance(files, dict) or not files:
            raise ValueError("invalid file manifest")
        if any(not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
               for digest in files.values()):
            raise ValueError("invalid digest")
        if set(names) != set(files) | required:
            raise ValueError("ZIP file set differs from signed manifest")
        for name, digest in files.items():
            if hashlib.sha256(bundle.read(name)).hexdigest() != digest:
                raise ValueError(f"payload hash mismatch: {name}")

    return {
        "archive_sha256": hashlib.sha256(raw).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "public_key_sha256": fingerprint,
    }


def verify_archive(archive: Path, expected_fingerprint: str) -> dict[str, str]:
    return verify_archive_bytes(archive.read_bytes(), expected_fingerprint)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--expected-key-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(verify_archive(args.archive, args.expected_key_sha256), indent=2))


if __name__ == "__main__":
    main()
