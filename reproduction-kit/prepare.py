"""Freeze candidate working trees and a realized Docker environment for handoff."""

import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weaver", type=Path, required=True)
    parser.add_argument("--cathedral", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", default="weaver-reproduction:candidate")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    origins = {}
    with tarfile.open(out / "sources.tar", "w") as archive:
        for name, root in [("Weaver_Os", args.weaver), ("cathedral-verified", args.cathedral)]:
            root = root.resolve()
            origins[name] = {
                "base_commit": command("git", "-C", str(root), "rev-parse", "HEAD"),
                "remote": command("git", "-C", str(root), "remote", "get-url", "origin"),
                "working_tree_status": command("git", "-C", str(root), "status", "--porcelain=v1"),
                "identity": "CANDIDATE_SNAPSHOT_NOT_BASE_COMMIT",
            }
            # Capture tracked plus unignored candidate files, never Git credentials,
            # ignored caches or wheel build inputs. Snapshot hash is the test identity.
            names = (
                subprocess.check_output(
                    [
                        "git",
                        "-C",
                        str(root),
                        "ls-files",
                        "-z",
                        "--cached",
                        "--others",
                        "--exclude-standard",
                    ]
                )
                .decode()
                .split("\0")
            )
            for relative in sorted(set(names) - {""}):
                path = root / relative
                if not path.exists():
                    continue
                if path.is_symlink() or not path.is_file():
                    raise ValueError(f"unsupported source entry: {path}")
                archive.add(path, arcname=f"{name}/{relative}", recursive=False)
    image_id = command("docker", "image", "inspect", "--format", "{{.Id}}", args.image)
    subprocess.run(["docker", "save", "-o", str(out / "environment.tar"), image_id], check=True)
    here = Path(__file__).resolve().parent
    for name in [
        "run.py",
        "README.md",
        "operator-receipt.template.json",
        "Dockerfile",
        "python.lock",
    ]:
        shutil.copyfile(here / name, out / name)
    metadata = {
        "schema": "weaver-cathedral-reproduction-v1",
        "sources": origins,
        "image_id": image_id,
        "platform": command(
            "docker", "image", "inspect", "--format", "{{.Os}}/{{.Architecture}}", image_id
        ),
        "evidence": "LOCAL_CANDIDATE",
        "witness": "W0",
        "authority": "O0",
        "production": "PROHIBITED",
        "independent_receipt": None,
    }
    (out / "kit.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (out / "SHA256SUMS").write_text(
        "".join(
            f"{digest(path)}  {path.name}\n" for path in sorted(out.iterdir()) if path.is_file()
        )
    )
    print(f"Manifest trust pin (deliver independently): {digest(out / 'SHA256SUMS')}")


if __name__ == "__main__":
    main()
