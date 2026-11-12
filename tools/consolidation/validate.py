"""Check consolidated asset identity and quarantine without executing donor archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "docs/consolidation/source-manifest.json"


def local_file(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts or not parts.parts:
        raise ValueError(f"invalid asset path: {relative}")
    path = root
    for part in parts.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"symlinked asset: {relative}")
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"asset missing or outside checkout: {relative}")
    return path


def validate(root: Path = ROOT) -> dict:
    manifest = json.loads(local_file(root, MANIFEST).read_text())
    if manifest.get("schema") != "weaver-consolidation-sources-1":
        raise ValueError("unsupported consolidation manifest")
    if (manifest.get("activation"), manifest.get("authority"), manifest.get("witness")) != (
        "none",
        "O0",
        "W0",
    ):
        raise ValueError("manifest cannot activate or promote donor capabilities")
    entries = manifest["entries"]
    if not isinstance(entries, list) or not entries:
        raise ValueError("empty asset manifest")
    seen = set()
    archives = 0
    for entry in entries:
        relative = entry["target"]
        if relative in seen:
            raise ValueError(f"duplicate target: {relative}")
        seen.add(relative)
        path = local_file(root, relative)
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["target_sha256"]:
            raise ValueError(f"asset digest mismatch: {relative}")
        if len(entry["source_commit"]) != 40 or len(entry["source_sha256"]) != 64:
            raise ValueError(f"invalid source pin: {relative}")
        if path.suffix == ".zip":
            if entry["disposition"] != "reference-only-not-runtime":
                raise ValueError("donor archive must remain reference-only")
            archives += 1
            with zipfile.ZipFile(path) as archive:
                members = archive.infolist()
                if len(members) > 4096 or sum(m.file_size for m in members) > 32 * 1024 * 1024:
                    raise ValueError("oversized donor archive")
                for member in members:
                    name = PurePosixPath(member.filename)
                    if name.is_absolute() or ".." in name.parts or "\\" in member.filename:
                        raise ValueError("unsafe archive member")
                    if stat.S_ISLNK(member.external_attr >> 16):
                        raise ValueError("symlink in donor archive")
    return {
        "schema": manifest["schema"],
        "assets_checked": len(seen),
        "reference_archives": archives,
        "activation": "none",
        "result": "PASS",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(validate(args.root), sort_keys=True))


if __name__ == "__main__":
    main()
