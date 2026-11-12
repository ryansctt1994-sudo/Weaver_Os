from __future__ import annotations

import hashlib
import json
import zipfile

import pytest

from tools.consolidation.validate import MANIFEST, ROOT, local_file, validate


def fixture_root(tmp_path):
    payload = tmp_path / "research" / "donor.zip"
    payload.parent.mkdir()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("LICENSE", "MIT")
    entry = {
        "target": "research/donor.zip",
        "target_sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
        "source_commit": "a" * 40,
        "source_sha256": "b" * 64,
        "disposition": "reference-only-not-runtime",
    }
    manifest = {
        "schema": "weaver-consolidation-sources-1",
        "activation": "none",
        "authority": "O0",
        "witness": "W0",
        "entries": [entry],
    }
    path = tmp_path / MANIFEST
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(manifest))
    return path, payload, manifest


def test_committed_assets_match_pinned_manifest():
    assert validate(ROOT)["reference_archives"] == 7


def test_modified_asset_is_refused(tmp_path):
    _, payload, _ = fixture_root(tmp_path)
    payload.write_bytes(b"changed")
    with pytest.raises(ValueError, match="digest"):
        validate(tmp_path)


@pytest.mark.parametrize("name", ["../outside", "/absolute"])
def test_escape_paths_are_refused(tmp_path, name):
    with pytest.raises(ValueError, match="path"):
        local_file(tmp_path, name)


def test_symlinked_ancestor_is_refused(tmp_path):
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "file").write_text("x")
    (tmp_path / "link").symlink_to(tmp_path / "real", target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        local_file(tmp_path, "link/file")


def test_archive_cannot_escape_when_retrieved(tmp_path):
    path, payload, manifest = fixture_root(tmp_path)
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("../outside", "x")
    manifest["entries"][0]["target_sha256"] = hashlib.sha256(payload.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="archive member"):
        validate(tmp_path)


def test_manifest_cannot_enable_a_donor(tmp_path):
    path, _, manifest = fixture_root(tmp_path)
    manifest["activation"] = "enabled"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="activate"):
        validate(tmp_path)
