from weaver_auth.bedrock.admission.admission_kernel import AdjudicationCase, evaluate_case


def test_valid_case_admitted() -> None:
    case = AdjudicationCase(
        case_id="test-1",
        evidence_hash="abc123",
        submitter="user-1",
        proposal="Valid proposal with evidence",
    )
    decision = evaluate_case(case)
    assert decision.status == "admit"


def test_empty_case_rejected() -> None:
    case = AdjudicationCase(
        case_id="",
        evidence_hash="",
        submitter="",
        proposal="",
    )
    decision = evaluate_case(case)
    assert decision.status == "reject"


def test_no_evidence_deferred() -> None:
    case = AdjudicationCase(
        case_id="test-2",
        evidence_hash="",
        submitter="user-2",
        proposal="Claim without evidence",
    )
    decision = evaluate_case(case)
    assert decision.status in {"defer", "reject"}
