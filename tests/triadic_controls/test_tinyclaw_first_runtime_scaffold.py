from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


REQUIRED_PATHS = [
    "BUILD_PACKAGE_B_MASTER_BUILD_V0_1_TINYCLAW_FIRST_RUNTIME.md",
    "evidence/external_repo_intake_manifest.yaml",
    "promotion/PROMOTION_GATE.md",
    "promotion/evidence_status_matrix.yaml",
    "promotion/authority_lease_registry.schema.json",
    "runtime/tinyclaw/TINYCLAW_ADAPTER.md",
    "runtime/tinyclaw/TINYCLAW_SECURITY_HARDENING.md",
    "runtime/tinyclaw/MESSAGE_QUEUE_RECEIPT_SPEC.md",
    "runtime/tinyclaw/TEAM_CHAIN_RECEIPT_SPEC.md",
    "runtime/tinyclaw/SENDER_PAIRING_POLICY.md",
    "runtime/tinyclaw/TINYOFFICE_OPERATOR_CONSOLE.md",
    "security/strix/STRIX_SCOPE_GATE.md",
    "security/strix/STRIX_REPORT_MAPPING.md",
    "security/strix/schemas/security_scan_receipt.schema.json",
    "security/strix/schemas/vulnerability_finding.schema.json",
    "security/strix/schemas/poc_validation_receipt.schema.json",
    "security/strix/schemas/fix_verification_receipt.schema.json",
    "robotics/rosclaw/SIMULATION_FIRST_POLICY.md",
    "robotics/rosclaw/ACTUATION_GATE.md",
    "robotics/rosclaw/ROSCLAW_TRANSPORT_POLICY.md",
    "robotics/rosclaw/allowed_topics.yaml",
    "robotics/rosclaw/workspace_limits.yaml",
    "robotics/rosclaw/estop_policy.md",
    "receipts/README_B_MASTER_BUILD_V0_1_TINYCLAW_FIRST_RUNTIME.md",
]


def test_tinyclaw_first_runtime_scaffold_files_exist():
    missing = [path for path in REQUIRED_PATHS if not (REPO_ROOT / path).exists()]
    assert missing == []


def test_tinyclaw_first_runtime_scaffold_declares_non_execution():
    joined = "\n".join((REPO_ROOT / path).read_text(encoding="utf-8") for path in REQUIRED_PATHS)
    assert "No runtime execution" in joined or "does not invoke" in joined
    assert "PHYSICAL_ACTUATION: BLOCKED_BY_DEFAULT" in joined or "physical_actuation" in joined
    assert "promotion_gate: HOLD" in joined or "PROMOTION_GATE: HOLD" in joined


def test_rosclaw_topics_are_fail_closed():
    text = (REPO_ROOT / "robotics/rosclaw/allowed_topics.yaml").read_text(encoding="utf-8")
    assert 'default: "deny"' in text
    assert 'mode: "simulation_only"' in text
    assert 'denied:' in text
    assert '- "*"' in text


def test_intake_manifest_keeps_promotion_on_hold():
    text = (REPO_ROOT / "evidence/external_repo_intake_manifest.yaml").read_text(encoding="utf-8")
    assert 'promotion_gate: "HOLD"' in text
    assert 'authority: "none"' in text
    assert "e912fd4d782e439238ce12c45f7ae924669388e9" in text
    assert "5d91500564e4a3436df1be54a85eb250cc331df8" in text
    assert "109ffabd9775208bed6f983715f3212790237cd7" in text
