import sys
sys.path.append("..")
from admission.admission_kernel import AdjudicationCase
from admission.pathology_scanner import scan_case


def test_scan_returns_flags():
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


def test_flags_are_non_blocking():
    case = AdjudicationCase(
        case_id="scan-2",
        evidence_hash="hash2",
        submitter="user-4",
        proposal="Another case",
    )
    try:
        scan_case(case)
    except Exception:
        assert False, "Scanner should not raise"
