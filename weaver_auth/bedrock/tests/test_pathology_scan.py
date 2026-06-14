from weaver_auth.bedrock.admission.admission_kernel import AdjudicationCase
from weaver_auth.bedrock.admission.pathology_scanner import scan_case


def test_scan_returns_flags() -> None:
    case = AdjudicationCase(
        case_id="scan-1",
        evidence_hash="hash",
        submitter="user-3",
        proposal="A normal case",
    )
    flags = scan_case(case)
    assert isinstance(flags, list)
    for flag in flags:
        assert flag.startswith("GP-")


def test_flags_are_non_blocking() -> None:
    case = AdjudicationCase(
        case_id="scan-2",
        evidence_hash="hash2",
        submitter="user-4",
        proposal="Another case",
    )
    scan_case(case)
