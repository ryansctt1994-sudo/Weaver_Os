from cathedral_core.witness.qgs import QGSLevel, evidence_sufficient


def test_qgs_levels_are_ordered():
    assert QGSLevel.E0_CLAIM < QGSLevel.E1_SPEC
    assert QGSLevel.E1_SPEC < QGSLevel.E2_IMPLEMENTED
    assert QGSLevel.E2_IMPLEMENTED < QGSLevel.E3_RECEIPTED
    assert QGSLevel.E3_RECEIPTED < QGSLevel.E4_REPLICATED
    assert QGSLevel.E4_REPLICATED < QGSLevel.E5_PRODUCTION_BOUND


def test_evidence_sufficient_accepts_equal_or_higher_level():
    assert evidence_sufficient(QGSLevel.E3_RECEIPTED, QGSLevel.E3_RECEIPTED)
    assert evidence_sufficient(QGSLevel.E4_REPLICATED, QGSLevel.E3_RECEIPTED)


def test_evidence_sufficient_rejects_lower_level():
    assert not evidence_sufficient(QGSLevel.E1_SPEC, QGSLevel.E3_RECEIPTED)
