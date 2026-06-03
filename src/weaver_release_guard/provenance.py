from __future__ import annotations

import hashlib
import json
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from .oidc import verify_oidc_token
from .utils import dump_json, fail, load_json, sha256_file


def generate_weaver_provenance(args) -> dict[str, Any]:
    dist_dir = Path(args.dist_dir)
    manifest_path = Path(args.manifest)
    slsa_path = Path(args.slsa)

    artifacts = sorted(
        [
            p
            for p in dist_dir.iterdir()
            if p.is_file() and (p.suffix in {".whl", ".zip"} or str(p).endswith(".tar.gz"))
        ]
    )
    if not artifacts:
        fail(f"No release artifacts found in {dist_dir}")

    artifact = artifacts[0]
    slsa = load_json(slsa_path)

    return {
        "schema_version": "1.0",
        "artifact": {
            "name": artifact.name,
            "version": args.version or "",
            "digests": {"sha256": sha256_file(artifact)},
        },
        "slsa_provenance": {
            "predicate_type": slsa.get("predicateType", ""),
            "statement_digest": sha256_file(slsa_path),
            "builder_id": slsa.get("predicate", {}).get("builder", {}).get("id", ""),
            "source_uri": slsa.get("predicate", {}).get("invocation", {}).get("configSource", {}).get("uri", ""),
            "source_commit": slsa.get("predicate", {}).get("invocation", {}).get("configSource", {}).get("digest", {}).get("sha1", ""),
        },
        "build": {
            "build_id": args.build_id,
            "workflow": args.workflow,
            "runner": args.runner,
            "started_at": args.started_at,
            "finished_at": args.finished_at,
            "materials_digest": sha256_file(manifest_path),
            "environment": {
                "repo": args.repo,
                "ref": args.ref,
                "sha": args.sha,
                "python_version": args.python_version,
            },
        },
        "governance": {
            "policy_version": args.policy_version,
            "lease_id": args.lease_id,
            "authority_level": args.authority_level,
            "reviewer": args.reviewer,
            "approval_ref": args.approval_ref,
        },
        "integrity": {
            "manifest_digest": sha256_file(manifest_path),
            "attestation_digest": hashlib.sha256(
                json.dumps(slsa, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "signature_key_id": args.signature_key_id,
        },
    }


def verify_weaver_provenance(artifact: Path, manifest: Path, weaver: Path, slsa: Path | None) -> None:
    manifest_obj = load_json(manifest)
    weaver_obj = load_json(weaver)

    artifact_sha256 = sha256_file(artifact)
    if weaver_obj["artifact"]["digests"]["sha256"] != artifact_sha256:
        fail("Artifact digest mismatch in Weaver provenance")

    if weaver_obj["integrity"]["manifest_digest"] != sha256_file(manifest):
        fail("Manifest digest mismatch in Weaver provenance")

    if weaver_obj["artifact"]["name"] not in manifest_obj:
        fail("Artifact missing from manifest")
    if manifest_obj[weaver_obj["artifact"]["name"]] != artifact_sha256:
        fail("Manifest entry does not match artifact digest")

    if not weaver_obj["build"].get("build_id"):
        fail("Missing build_id")
    if not weaver_obj["governance"].get("policy_version"):
        fail("Missing policy_version")
    if not weaver_obj["governance"].get("lease_id"):
        fail("Missing lease_id")
    if weaver_obj["governance"].get("authority_level") is None:
        fail("Missing authority_level")

    if slsa:
        slsa_obj = load_json(slsa)
        if weaver_obj["slsa_provenance"]["predicate_type"] != slsa_obj.get("predicateType", ""):
            fail("SLSA predicate type mismatch")
        if weaver_obj["slsa_provenance"]["statement_digest"] != sha256_file(slsa):
            fail("SLSA statement digest mismatch")


def build_parser() -> ArgumentParser:
    from .cli import build_parser as _build

    return _build()


def cmd_generate(args) -> None:
    dump_json(generate_weaver_provenance(args), Path(args.out) if args.out else None)


def cmd_verify(args) -> None:
    _ = verify_oidc_token(args.jwt) if getattr(args, "jwt", "") else None
    verify_weaver_provenance(
        Path(args.artifact),
        Path(args.manifest),
        Path(args.weaver),
        Path(args.slsa) if args.slsa else None,
    )
    print("Weaver provenance verification passed")
