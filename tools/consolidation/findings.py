"""Deterministic, evidence-only confirmation for defensive test findings.

The confirmation protocol is deliberately separated from test execution:

1. Verify that the declared target is inside an explicit scope boundary.
2. Require a baseline observation and at least two test observations.
3. Compare structured measurements and require a reproducible difference.
4. Suppress duplicate target/vector findings within the supplied registry.
5. Emit a deterministic receipt hash over the decision.

No request payloads, credentials, exploit logic, or remote-execution behavior
belong in this module. A confirmed result is evidence, not authorization.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from types import MappingProxyType
from typing import Literal, TypeAlias

Scalar: TypeAlias = str | int | float | bool | None
# key, baseline_present, baseline_value, observed_present, observed_value
Difference: TypeAlias = tuple[str, bool, Scalar, bool, Scalar]
ConfirmationStatus: TypeAlias = Literal["CONFIRMED", "REJECTED", "DUPLICATE"]


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _validate_scalar(value: Scalar) -> None:
    if not isinstance(value, (str, int, float, bool, type(None))):
        raise ValueError("measurements must contain JSON scalar values only")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("measurements must not contain NaN or infinite values")


@dataclass(frozen=True)
class ScopeBoundary:
    """An explicit, exact-match target allowlist.

    Exact matching is intentional. Broader domain or network expansion belongs
    in an independently reviewed scope resolver, not in finding confirmation.
    Boundary membership is necessary but does not itself prove that execution
    was legally or organizationally authorized.
    """

    scope_id: str
    allowed_targets: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_targets", frozenset(self.allowed_targets))
        if not self.scope_id:
            raise ValueError("scope_id must not be empty")
        if not self.allowed_targets or any(not target for target in self.allowed_targets):
            raise ValueError("allowed_targets must contain non-empty exact targets")

    def contains(self, target: str) -> bool:
        return target in self.allowed_targets


@dataclass(frozen=True)
class Observation:
    """A structured measurement captured outside this module."""

    observation_id: str
    target: str
    measurements: Mapping[str, Scalar]

    def __post_init__(self) -> None:
        if not self.observation_id:
            raise ValueError("observation_id must not be empty")
        if not self.target:
            raise ValueError("target must not be empty")
        if not self.measurements:
            raise ValueError("measurements must not be empty")
        if any(not key for key in self.measurements):
            raise ValueError("measurement keys must not be empty")
        for value in self.measurements.values():
            _validate_scalar(value)
        object.__setattr__(self, "measurements", MappingProxyType(dict(self.measurements)))

    def canonical_measurements(self) -> dict[str, Scalar]:
        return {key: self.measurements[key] for key in sorted(self.measurements)}

    def digest(self) -> str:
        payload = {
            "measurements": self.canonical_measurements(),
            "observation_id": self.observation_id,
            "target": self.target,
            "version": "weaver.finding.observation.v1",
        }
        return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ConfirmationResult:
    """Evidence-only result; never an execution or promotion authorization."""

    status: ConfirmationStatus
    reason: str
    scope_id: str
    target: str
    test_vector: str
    fingerprint: str
    baseline_digest: str
    test_run_digests: tuple[str, ...]
    differences: tuple[Difference, ...]
    receipt_hash: str
    authority: Literal["EVIDENCE_ONLY"] = "EVIDENCE_ONLY"
    operational_authority: Literal["O0"] = "O0"


@dataclass
class FindingRegistry:
    """Session-local duplicate suppression for confirmed findings."""

    _fingerprints: set[str] = field(default_factory=set)

    def contains(self, fingerprint: str) -> bool:
        return fingerprint in self._fingerprints

    def record(self, fingerprint: str) -> None:
        self._fingerprints.add(fingerprint)


def finding_fingerprint(scope_id: str, target: str, test_vector: str) -> str:
    """Bind duplicate identity to scope, exact target, and declared vector."""

    payload = {
        "scope_id": scope_id,
        "target": target,
        "test_vector": test_vector,
        "version": "weaver.finding.fingerprint.v1",
    }
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _differences(baseline: Observation, observed: Observation) -> tuple[Difference, ...]:
    keys = sorted(set(baseline.measurements) | set(observed.measurements))
    differences: list[Difference] = []

    for key in keys:
        baseline_present = key in baseline.measurements
        observed_present = key in observed.measurements
        baseline_value = baseline.measurements[key] if baseline_present else None
        observed_value = observed.measurements[key] if observed_present else None

        values_equal = baseline_present == observed_present and (
            not baseline_present
            or _canonical_json(baseline_value) == _canonical_json(observed_value)
        )
        if not values_equal:
            differences.append(
                (
                    key,
                    baseline_present,
                    baseline_value,
                    observed_present,
                    observed_value,
                )
            )

    return tuple(differences)


def _receipt_hash(
    *,
    status: ConfirmationStatus,
    reason: str,
    scope_id: str,
    target: str,
    test_vector: str,
    fingerprint: str,
    baseline_digest: str,
    test_run_digests: tuple[str, ...],
    differences: tuple[Difference, ...],
) -> str:
    payload = {
        "authority": "EVIDENCE_ONLY",
        "baseline_digest": baseline_digest,
        "differences": differences,
        "fingerprint": fingerprint,
        "operational_authority": "O0",
        "reason": reason,
        "scope_id": scope_id,
        "status": status,
        "target": target,
        "test_run_digests": test_run_digests,
        "test_vector": test_vector,
        "version": "weaver.finding.confirmation.v1",
    }
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _result(
    *,
    status: ConfirmationStatus,
    reason: str,
    scope_id: str,
    target: str,
    test_vector: str,
    fingerprint: str,
    baseline_digest: str,
    test_run_digests: tuple[str, ...],
    differences: tuple[Difference, ...] = (),
) -> ConfirmationResult:
    return ConfirmationResult(
        status=status,
        reason=reason,
        scope_id=scope_id,
        target=target,
        test_vector=test_vector,
        fingerprint=fingerprint,
        baseline_digest=baseline_digest,
        test_run_digests=test_run_digests,
        differences=differences,
        receipt_hash=_receipt_hash(
            status=status,
            reason=reason,
            scope_id=scope_id,
            target=target,
            test_vector=test_vector,
            fingerprint=fingerprint,
            baseline_digest=baseline_digest,
            test_run_digests=test_run_digests,
            differences=differences,
        ),
    )


def confirm_finding(
    *,
    scope: ScopeBoundary,
    target: str,
    test_vector: str,
    baseline: Observation,
    test_runs: tuple[Observation, ...],
    registry: FindingRegistry,
) -> ConfirmationResult:
    """Confirm a finding through scope, baseline, test, and comparison gates."""

    fingerprint = finding_fingerprint(scope.scope_id, target, test_vector)
    baseline_digest = baseline.digest()
    test_run_digests = tuple(run.digest() for run in test_runs)

    if not target or not test_vector:
        return _result(
            status="REJECTED",
            reason="invalid_target_or_test_vector",
            scope_id=scope.scope_id,
            target=target,
            test_vector=test_vector,
            fingerprint=fingerprint,
            baseline_digest=baseline_digest,
            test_run_digests=test_run_digests,
        )

    if not scope.contains(target):
        return _result(
            status="REJECTED",
            reason="target_outside_scope_boundary",
            scope_id=scope.scope_id,
            target=target,
            test_vector=test_vector,
            fingerprint=fingerprint,
            baseline_digest=baseline_digest,
            test_run_digests=test_run_digests,
        )

    if baseline.target != target:
        return _result(
            status="REJECTED",
            reason="baseline_target_mismatch",
            scope_id=scope.scope_id,
            target=target,
            test_vector=test_vector,
            fingerprint=fingerprint,
            baseline_digest=baseline_digest,
            test_run_digests=test_run_digests,
        )

    if len(test_runs) < 2:
        return _result(
            status="REJECTED",
            reason="insufficient_reproduction_runs",
            scope_id=scope.scope_id,
            target=target,
            test_vector=test_vector,
            fingerprint=fingerprint,
            baseline_digest=baseline_digest,
            test_run_digests=test_run_digests,
        )

    if any(run.target != target for run in test_runs):
        return _result(
            status="REJECTED",
            reason="test_target_mismatch",
            scope_id=scope.scope_id,
            target=target,
            test_vector=test_vector,
            fingerprint=fingerprint,
            baseline_digest=baseline_digest,
            test_run_digests=test_run_digests,
        )

    observed_differences = tuple(_differences(baseline, run) for run in test_runs)
    first = observed_differences[0]

    if not first:
        return _result(
            status="REJECTED",
            reason="no_measurable_difference",
            scope_id=scope.scope_id,
            target=target,
            test_vector=test_vector,
            fingerprint=fingerprint,
            baseline_digest=baseline_digest,
            test_run_digests=test_run_digests,
        )

    if any(differences != first for differences in observed_differences[1:]):
        return _result(
            status="REJECTED",
            reason="non_reproducible_difference",
            scope_id=scope.scope_id,
            target=target,
            test_vector=test_vector,
            fingerprint=fingerprint,
            baseline_digest=baseline_digest,
            test_run_digests=test_run_digests,
        )

    if registry.contains(fingerprint):
        return _result(
            status="DUPLICATE",
            reason="duplicate_scope_target_vector",
            scope_id=scope.scope_id,
            target=target,
            test_vector=test_vector,
            fingerprint=fingerprint,
            baseline_digest=baseline_digest,
            test_run_digests=test_run_digests,
            differences=first,
        )

    registry.record(fingerprint)
    return _result(
        status="CONFIRMED",
        reason="scope_bound_reproducible_difference",
        scope_id=scope.scope_id,
        target=target,
        test_vector=test_vector,
        fingerprint=fingerprint,
        baseline_digest=baseline_digest,
        test_run_digests=test_run_digests,
        differences=first,
    )
