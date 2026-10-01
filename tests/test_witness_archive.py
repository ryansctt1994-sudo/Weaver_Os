"""Adversarial checks for the external archive verifier."""

import base64
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from tools.verify_witness_archive import verify_archive

ARCHIVE = (
    Path(__file__).resolve().parents[1]
    / "releases/weaver-witness-signed-rc1/WEAVER_WITNESS_SIGNED_RC1.zip"
)
EXPECTED = "5ac8e9d25de8d37cd9165d4a7458c34634aeded53c1709573ddf4cc122bcefb9"


def rewrite(tmp_path, mutate):
    with zipfile.ZipFile(ARCHIVE) as source:
        files = {name: source.read(name) for name in source.namelist()}
    mutate(files)
    output = tmp_path / "changed.zip"
    with zipfile.ZipFile(output, "w") as target:
        for name, data in files.items():
            target.writestr(name, data)
    return output


def test_original_passes():
    assert verify_archive(ARCHIVE, EXPECTED)["public_key_sha256"] == EXPECTED


def test_payload_mutation_is_rejected(tmp_path):
    archive = rewrite(tmp_path, lambda files: files.__setitem__("src/weaver_core.py", b"changed"))
    with pytest.raises(ValueError, match="payload hash mismatch"):
        verify_archive(archive, EXPECTED)


def test_whole_signature_substitution_is_rejected(tmp_path):
    def substitute(files):
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        files["PUBLIC_KEY.b64"] = base64.b64encode(public) + b"\n"
        files["MANIFEST.sig"] = base64.b64encode(key.sign(files["MANIFEST.json"])) + b"\n"

    archive = rewrite(tmp_path, substitute)
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        verify_archive(archive, EXPECTED)


def test_zip_traversal_is_rejected(tmp_path):
    archive = rewrite(tmp_path, lambda files: files.__setitem__("../outside.txt", b"x"))
    with pytest.raises(ValueError, match="unsafe ZIP entry"):
        verify_archive(archive, EXPECTED)
