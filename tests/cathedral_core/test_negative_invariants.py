from pathlib import Path

import pytest

from cathedral_core.constitution_loader import InvariantLoadError, load_negative_invariants


REQUIRED_INVARIANT_IDS = {
    "NoSilentConversionOfUncertaintyIntoAuthority",
    "ProposalIsNotAuthority",
    "ObservationIsNotParticipation",
    "PaperIsNotEvidence",
    "AuthorityOutsideScopeIsNoAuthority",
    "MythicContentIsQuarantined",
}


def test_negative_invariants_file_loads_required_ids():
    invariants = load_negative_invariants("constitution/negative_invariants.yaml")
    invariant_ids = {invariant.id for invariant in invariants}

    assert REQUIRED_INVARIANT_IDS <= invariant_ids


def test_negative_invariants_are_fail_closed():
    invariants = load_negative_invariants("constitution/negative_invariants.yaml")

    assert invariants
    assert all(invariant.severity == "fail_closed" for invariant in invariants)


def test_negative_invariant_loader_rejects_missing_required_field(tmp_path: Path):
    malformed = tmp_path / "negative_invariants.yaml"
    malformed.write_text(
        "negative_invariants:\n"
        "  - id: ProposalIsNotAuthority\n"
        "    statement: Proposal generation cannot authorize execution.\n",
        encoding="utf-8",
    )

    with pytest.raises(InvariantLoadError):
        load_negative_invariants(malformed)
