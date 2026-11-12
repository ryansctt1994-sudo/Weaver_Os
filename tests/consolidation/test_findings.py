from tools.consolidation.findings import (
    FindingRegistry,
    Observation,
    ScopeBoundary,
    confirm_finding,
    finding_fingerprint,
)

TARGET = "service://synthetic-api"


def observation(observation_id: str, *, status: int, role: str = "viewer") -> Observation:
    return Observation(
        observation_id=observation_id,
        target=TARGET,
        measurements={"response_status": status, "observed_role": role},
    )


def confirm(registry: FindingRegistry | None = None):
    return confirm_finding(
        scope=ScopeBoundary("scope-001", frozenset({TARGET})),
        target=TARGET,
        test_vector="authorization-boundary-check",
        baseline=observation("baseline", status=403),
        test_runs=(
            observation("test-1", status=200, role="admin"),
            observation("test-2", status=200, role="admin"),
        ),
        registry=registry or FindingRegistry(),
    )


def test_confirms_scope_bound_reproducible_difference_with_o0_receipt():
    result = confirm()

    assert result.status == "CONFIRMED"
    assert result.reason == "scope_bound_reproducible_difference"
    assert result.authority == "EVIDENCE_ONLY"
    assert result.operational_authority == "O0"
    assert len(result.receipt_hash) == 64
    assert result.differences == (
        ("observed_role", True, "viewer", True, "admin"),
        ("response_status", True, 403, True, 200),
    )


def test_rejects_target_outside_exact_scope_boundary():
    result = confirm_finding(
        scope=ScopeBoundary("scope-001", frozenset({"service://other"})),
        target=TARGET,
        test_vector="authorization-boundary-check",
        baseline=observation("baseline", status=403),
        test_runs=(observation("test-1", status=200), observation("test-2", status=200)),
        registry=FindingRegistry(),
    )

    assert result.status == "REJECTED"
    assert result.reason == "target_outside_scope_boundary"


def test_rejects_a_single_test_run_as_not_reproduced():
    result = confirm_finding(
        scope=ScopeBoundary("scope-001", frozenset({TARGET})),
        target=TARGET,
        test_vector="authorization-boundary-check",
        baseline=observation("baseline", status=403),
        test_runs=(observation("test-1", status=200),),
        registry=FindingRegistry(),
    )

    assert result.status == "REJECTED"
    assert result.reason == "insufficient_reproduction_runs"


def test_rejects_when_comparison_has_no_measurable_difference():
    result = confirm_finding(
        scope=ScopeBoundary("scope-001", frozenset({TARGET})),
        target=TARGET,
        test_vector="authorization-boundary-check",
        baseline=observation("baseline", status=403),
        test_runs=(observation("test-1", status=403), observation("test-2", status=403)),
        registry=FindingRegistry(),
    )

    assert result.status == "REJECTED"
    assert result.reason == "no_measurable_difference"


def test_rejects_non_reproducible_differences():
    result = confirm_finding(
        scope=ScopeBoundary("scope-001", frozenset({TARGET})),
        target=TARGET,
        test_vector="authorization-boundary-check",
        baseline=observation("baseline", status=403),
        test_runs=(
            observation("test-1", status=200, role="admin"),
            observation("test-2", status=201, role="editor"),
        ),
        registry=FindingRegistry(),
    )

    assert result.status == "REJECTED"
    assert result.reason == "non_reproducible_difference"


def test_suppresses_duplicate_scope_target_vector():
    registry = FindingRegistry()

    first = confirm(registry)
    second = confirm(registry)

    assert first.status == "CONFIRMED"
    assert second.status == "DUPLICATE"
    assert second.reason == "duplicate_scope_target_vector"


def test_fingerprint_is_deterministic_and_scope_bound():
    first = finding_fingerprint("scope-001", TARGET, "vector-a")
    repeated = finding_fingerprint("scope-001", TARGET, "vector-a")
    different_scope = finding_fingerprint("scope-002", TARGET, "vector-a")

    assert first == repeated
    assert first != different_scope


def test_receipt_is_deterministic_and_binds_observation_digests():
    first = confirm()
    repeated = confirm()

    assert first.receipt_hash == repeated.receipt_hash
    assert first.baseline_digest
    assert len(first.test_run_digests) == 2
    assert first.test_run_digests[0] != first.test_run_digests[1]


def test_distinguishes_missing_measurement_from_explicit_null():
    baseline = Observation("baseline", TARGET, {"stable": 1})
    first = Observation("test-1", TARGET, {"stable": 1, "optional": None})
    second = Observation("test-2", TARGET, {"stable": 1, "optional": None})

    result = confirm_finding(
        scope=ScopeBoundary("scope-001", frozenset({TARGET})),
        target=TARGET,
        test_vector="schema-presence-check",
        baseline=baseline,
        test_runs=(first, second),
        registry=FindingRegistry(),
    )

    assert result.status == "CONFIRMED"
    assert result.differences == (("optional", False, None, True, None),)


def test_distinguishes_boolean_from_integer_measurement():
    baseline = Observation("baseline", TARGET, {"flag": True})
    first = Observation("test-1", TARGET, {"flag": 1})
    second = Observation("test-2", TARGET, {"flag": 1})

    result = confirm_finding(
        scope=ScopeBoundary("scope-001", frozenset({TARGET})),
        target=TARGET,
        test_vector="measurement-type-check",
        baseline=baseline,
        test_runs=(first, second),
        registry=FindingRegistry(),
    )

    assert result.status == "CONFIRMED"
    assert result.differences == (("flag", True, True, True, 1),)


def test_observation_copies_measurements_before_digesting():
    measurements = {"response_status": 403}
    captured = Observation("baseline", TARGET, measurements)

    measurements["response_status"] = 200

    assert captured.measurements["response_status"] == 403
