"""Legacy report bytes remain distinct from new authority-bearing data."""

import pytest
import rfc8785
from weaver_contracts.canonical import CanonicalizationError, canonicalize

from tools.claim_audit.legacy_canonical import JCS_RFC8785
from tools.claim_audit.legacy_canonical import canonicalize as legacy


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        {"x": 1.0},
        {"x": -0.0},
        {"x": 1e-7},
        {"x": 1e21},
        {"\U0001f600": 1, "\ue000": 2},
        {"x": "é"},
    ],
)
def test_retained_report_profile_matches_the_reference_vectors(value):
    assert legacy(value, JCS_RFC8785).encode() == rfc8785.dumps(value)


def test_legacy_float_acceptance_never_changes_weaver_authority_profile():
    assert legacy({"value": 1.5}) == '{"value":1.5}'
    with pytest.raises(CanonicalizationError):
        canonicalize({"value": 1.5})
