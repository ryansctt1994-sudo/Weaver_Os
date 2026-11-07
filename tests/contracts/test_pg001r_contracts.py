import hashlib
import json
from pathlib import Path

import pytest
from weaver_contracts import pg001r
from weaver_contracts.pg001r import (
    AUTHORITY_EVIDENCE_FLOOR,
    AuthorityLevel,
    ContractError,
    EvidenceLevel,
    PromotionRequest,
)

ROOT = Path(__file__).resolve().parents[2]
NEXUS_SHA256 = "37e3fb44b1b0d75bf821d3a98ba837a95a7baa41c28e466da118f63494b6ff8f"


def _payload(**overrides):
    base = {
        "artifact_id": "PG-001R-TEST",
        "current_evidence_level": "R0",
        "verified_evidence_level": "R1",
        "requested_evidence_level": "R1",
        "requested_authority": "NONE",
        "required_evidence": ["spec"],
        "verified_evidence": ["spec"],
        "recorded_evidence": ["spec"],
        "open_contradictions": [],
        "recovery_dependencies_required": [],
        "recovery_dependencies_present": [],
        "self_issued_receipt_only": True,
        "independent_reproduction_receipts": 0,
        "external_publication_claimed_as_evidence": False,
        "external_publication_receipt_bound": False,
        "governance_bundle_id": None,
        "gate_decision_id": None,
        "human_authority_id": None,
        "clinical_scope": False,
        "clinical_safety_level": "NOT_APPLICABLE",
    }
    base.update(overrides)
    return base


def test_source_is_byte_identical_to_nexus_manifest_entry():
    """The file was moved verbatim; its identity is the Nexus manifest hash."""
    source = Path(pg001r.__file__).read_bytes()
    assert hashlib.sha256(source).hexdigest() == NEXUS_SHA256


def test_evidence_levels_match_ratified_crosswalk():
    crosswalk = json.loads((ROOT / "governance/evidence_crosswalk.json").read_text())
    ladder = [level["level"] for level in crosswalk["target_ladder"]["levels"]]
    assert [level.name for level in EvidenceLevel] == ladder


def test_production_needs_r6_and_pilot_needs_r4():
    assert AUTHORITY_EVIDENCE_FLOOR[AuthorityLevel.PRODUCTION] is EvidenceLevel.R6
    assert AUTHORITY_EVIDENCE_FLOOR[AuthorityLevel.PILOT] is EvidenceLevel.R4


def test_valid_request_round_trips():
    request = PromotionRequest.from_mapping(_payload())
    assert request.to_primitive() == _payload()


def test_unknown_field_rejected():
    with pytest.raises(ContractError, match="unsupported"):
        PromotionRequest.from_mapping(_payload(extra=True))


def test_missing_field_rejected():
    payload = _payload()
    del payload["artifact_id"]
    with pytest.raises(ContractError, match="missing"):
        PromotionRequest.from_mapping(payload)


@pytest.mark.parametrize(
    "overrides, match",
    [
        ({"current_evidence_level": "R2", "requested_evidence_level": "R1"}, "lower"),
        ({"requested_evidence_level": "R7"}, "unknown evidence level"),
        ({"requested_evidence_level": 2}, "must be strings"),
        ({"requested_authority": "ROOT"}, "unknown authority level"),
        ({"artifact_id": "TBD"}, "placeholder"),
        ({"required_evidence": ["a", "a"]}, "duplicate"),
        ({"required_evidence": "spec"}, "array"),
        ({"independent_reproduction_receipts": -1}, "non-negative"),
        ({"independent_reproduction_receipts": True}, "non-negative"),
        ({"self_issued_receipt_only": 1}, "boolean"),
        ({"clinical_safety_level": "C9"}, "clinical"),
    ],
)
def test_contract_rejections(overrides, match):
    with pytest.raises(ContractError, match=match):
        PromotionRequest.from_mapping(_payload(**overrides))
