"""RECEIPT_BINDING_GATE_v1 — standalone receipt admissibility gate.

Core invariant: no receipt may become VERIFIED unless all three gates pass:

1. Hash verification
   The receipt's declared hashes must equal recomputed artifact-tree hashes.

2. Replay verification
   The replay command must exit 0.

3. Negative-control rejection
   The negative-control command must exit non-zero. That command is expected
   to exercise a known forged/invalid receipt and fail when the forgery is
   correctly rejected. If the negative control exits 0, the gate itself has not
   demonstrated its rejection path (P12 Gate Self-Falsification).

Result states:
    VERIFIED
    REJECTED_HASH_MISMATCH
    REJECTED_REPLAY_FAILED
    REJECTED_NEGATIVE_CONTROL_FAILED
    ERROR

Gates are ordered and short-circuit: the first failure determines the state.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Sequence, Union

CHUNK = 1 << 16


class Status(str, Enum):
    VERIFIED = "VERIFIED"
    REJECTED_HASH_MISMATCH = "REJECTED_HASH_MISMATCH"
    REJECTED_REPLAY_FAILED = "REJECTED_REPLAY_FAILED"
    REJECTED_NEGATIVE_CONTROL_FAILED = "REJECTED_NEGATIVE_CONTROL_FAILED"
    ERROR = "ERROR"


@dataclass
class ReceiptBindingResult:
    status: Status
    reason: str = ""
    hash_diffs: Dict[str, Dict[str, Optional[str]]] = field(default_factory=dict)
    replay_returncode: Optional[int] = None
    negative_control_returncode: Optional[int] = None

    @property
    def verified(self) -> bool:
        return self.status is Status.VERIFIED

    def __bool__(self) -> bool:
        return self.verified


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def _safe_join(root: str, rel: str) -> str:
    if not isinstance(rel, str) or not rel:
        raise ValueError(f"invalid receipt path: {rel!r}")
    if os.path.isabs(rel):
        raise ValueError(f"absolute paths are not allowed in receipts: {rel!r}")

    root_real = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(root_real, rel))
    if os.path.commonpath([root_real, candidate]) != root_real:
        raise ValueError(f"receipt path escapes artifact_root: {rel!r}")
    return candidate


def _run(command: Union[str, Sequence[str]], cwd: Optional[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        shell=isinstance(command, str),
        capture_output=True,
        text=True,
    )


def bind_receipt(
    receipt: dict,
    artifact_root: str,
    replay_command: Union[str, Sequence[str]],
    negative_control_command: Union[str, Sequence[str]],
) -> ReceiptBindingResult:
    """Run the three mandatory gates in order.

    receipt:
        A dict containing a non-empty "hashes" map of
        {relative_path_under_artifact_root: sha256_hex}. A receipt declaring no
        hashes cannot be VERIFIED because it binds nothing.

    artifact_root:
        Root directory used for hash recomputation and as subprocess cwd.

    replay_command:
        Command that must exit 0.

    negative_control_command:
        Command expected to fail non-zero when a known forged/invalid receipt is
        correctly rejected. A zero exit means the rejection path was not proven.
    """

    try:
        if not isinstance(receipt, dict):
            return ReceiptBindingResult(Status.ERROR, "receipt is not a dict")

        declared = receipt.get("hashes")
        if not isinstance(declared, dict) or not declared:
            return ReceiptBindingResult(Status.ERROR, "receipt declares no hashes to bind")

        if not os.path.isdir(artifact_root):
            return ReceiptBindingResult(Status.ERROR, f"artifact_root not found: {artifact_root}")

        artifact_root = os.path.realpath(artifact_root)
    except Exception as exc:  # pragma: no cover - defensive
        return ReceiptBindingResult(Status.ERROR, f"validation error: {exc!r}")

    # Gate 1: hash verification.
    diffs: Dict[str, Dict[str, Optional[str]]] = {}
    for rel, declared_hash in declared.items():
        try:
            abspath = _safe_join(artifact_root, rel)
        except ValueError as exc:
            return ReceiptBindingResult(Status.ERROR, str(exc))

        if not isinstance(declared_hash, str) or len(declared_hash) != 64:
            diffs[rel] = {"declared": str(declared_hash), "actual": None}
            continue

        if not os.path.isfile(abspath):
            diffs[rel] = {"declared": declared_hash, "actual": None}
            continue

        actual = sha256_file(abspath)
        if actual != declared_hash.lower():
            diffs[rel] = {"declared": declared_hash, "actual": actual}

    if diffs:
        return ReceiptBindingResult(
            Status.REJECTED_HASH_MISMATCH,
            reason=f"{len(diffs)} hash mismatch(es)",
            hash_diffs=diffs,
        )

    # Gate 2: replay verification.
    try:
        replay = _run(replay_command, artifact_root)
    except Exception as exc:
        return ReceiptBindingResult(Status.ERROR, f"replay command failed to launch: {exc!r}")

    if replay.returncode != 0:
        return ReceiptBindingResult(
            Status.REJECTED_REPLAY_FAILED,
            reason=(replay.stderr or replay.stdout or "").strip()[:500],
            replay_returncode=replay.returncode,
        )

    # Gate 3: negative-control rejection. Non-zero is the expected success path.
    try:
        neg = _run(negative_control_command, artifact_root)
    except Exception as exc:
        return ReceiptBindingResult(
            Status.ERROR,
            f"negative-control command failed to launch: {exc!r}",
            replay_returncode=replay.returncode,
        )

    if neg.returncode == 0:
        return ReceiptBindingResult(
            Status.REJECTED_NEGATIVE_CONTROL_FAILED,
            reason="negative control exited 0: forgery was NOT rejected (gate unverified)",
            replay_returncode=replay.returncode,
            negative_control_returncode=neg.returncode,
        )

    return ReceiptBindingResult(
        Status.VERIFIED,
        reason="hash + replay + negative-control all passed",
        replay_returncode=replay.returncode,
        negative_control_returncode=neg.returncode,
    )
