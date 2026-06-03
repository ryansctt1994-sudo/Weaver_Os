"""Evidence registry for Cathedral MVP-0.

The registry records artifact maturity through QGS levels.  It does not decide
truth, safety, or production readiness; it preserves the current evidence class
and the basis for the claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .qgs import QGSLevel


@dataclass(frozen=True)
class EvidenceEvent:
    artifact_id: str
    previous_level: QGSLevel
    new_level: QGSLevel
    basis: str
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EvidenceRecord:
    artifact_id: str
    level: QGSLevel
    basis: str
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    history: list[EvidenceEvent] = field(default_factory=list)


class EvidenceRegistryError(ValueError):
    """Raised when evidence registry operations are invalid."""


class EvidenceRegistry:
    """In-memory QGS evidence registry.

    This is an MVP-0 registry intended for deterministic tests and later
    Chronicle/replay integration.  Persistence and hash-chaining belong in a
    later witness/chronicle layer.
    """

    def __init__(self) -> None:
        self._records: dict[str, EvidenceRecord] = {}

    def register(self, artifact_id: str, level: QGSLevel, basis: str) -> EvidenceRecord:
        """Register a new artifact at a QGS level."""

        artifact_id = artifact_id.strip()
        basis = basis.strip()
        if not artifact_id:
            raise EvidenceRegistryError("artifact_id is required")
        if not basis:
            raise EvidenceRegistryError("basis is required")
        if artifact_id in self._records:
            raise EvidenceRegistryError(f"artifact already registered: {artifact_id}")

        record = EvidenceRecord(artifact_id=artifact_id, level=level, basis=basis)
        self._records[artifact_id] = record
        return record

    def get(self, artifact_id: str) -> EvidenceRecord:
        """Return the evidence record for an artifact."""

        try:
            return self._records[artifact_id]
        except KeyError as exc:
            raise EvidenceRegistryError(f"artifact is not registered: {artifact_id}") from exc

    def promote(self, artifact_id: str, new_level: QGSLevel, basis: str) -> EvidenceRecord:
        """Promote an artifact to a higher QGS level.

        Promotion must be monotonic: the new level must be greater than the
        current level.  Equal-level restatement and downgrades are rejected in
        this MVP-0 path to avoid silent evidence inflation or ambiguity.
        """

        basis = basis.strip()
        if not basis:
            raise EvidenceRegistryError("basis is required")

        record = self.get(artifact_id)
        if new_level <= record.level:
            raise EvidenceRegistryError(
                f"promotion must increase QGS level: {record.level.name} -> {new_level.name}"
            )

        event = EvidenceEvent(
            artifact_id=artifact_id,
            previous_level=record.level,
            new_level=new_level,
            basis=basis,
        )
        record.history.append(event)
        record.level = new_level
        record.basis = basis
        record.updated_at = event.recorded_at
        return record

    def list_records(self) -> list[EvidenceRecord]:
        """Return all records in deterministic artifact-id order."""

        return [self._records[key] for key in sorted(self._records)]
