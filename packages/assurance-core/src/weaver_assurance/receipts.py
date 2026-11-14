"""Immutable evidence receipts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .canonical import sha256_json


@dataclass(frozen=True)
class EvidenceReceipt:
    version: str
    receipt_id: str
    subject: str
    producer: str
    policy_version: str
    evidence_level: str
    input_hashes: dict[str, str]
    output_hashes: dict[str, str]
    command: tuple[str, ...]
    exit_code: int
    environment_hash: str
    replay_status: str
    created_at: str
    receipt_hash: str

    @classmethod
    def create(
        cls,
        *,
        receipt_id: str,
        subject: str,
        producer: str,
        policy_version: str,
        evidence_level: str,
        input_hashes: dict[str, str],
        output_hashes: dict[str, str],
        command: tuple[str, ...],
        exit_code: int,
        environment_hash: str,
        replay_status: str,
        created_at: str,
    ) -> "EvidenceReceipt":
        base = {
            "version": "weaver.evidence.receipt.v1",
            "receipt_id": receipt_id,
            "subject": subject,
            "producer": producer,
            "policy_version": policy_version,
            "evidence_level": evidence_level,
            "input_hashes": input_hashes,
            "output_hashes": output_hashes,
            "command": list(command),
            "exit_code": int(exit_code),
            "environment_hash": environment_hash,
            "replay_status": replay_status,
            "created_at": created_at,
        }
        return cls(
            **{**base, "command": command},
            receipt_hash=sha256_json(base),
        )

    def verify(self) -> bool:
        value = asdict(self)
        claimed = value.pop("receipt_hash")
        value["command"] = list(value["command"])
        return claimed == sha256_json(value)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["command"] = list(value["command"])
        return value

