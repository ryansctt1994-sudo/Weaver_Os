"""Require targeted verifier gate removals to be detected by adversarial tests."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MUTATIONS = [
    (
        "archive-key-pin",
        "tools/verify_witness_archive.py",
        "if fingerprint != expected_fingerprint:",
        "if False:",
        "tests/test_witness_archive.py::test_whole_signature_substitution_is_rejected",
    ),
    (
        "archive-signature",
        "tools/verify_witness_archive.py",
        "Ed25519PublicKey.from_public_bytes(public).verify(signature, manifest_bytes)",
        "pass  # intentionally disabled by mutation probe",
        "tests/test_witness_archive.py::test_invalid_signature_is_rejected",
    ),
    (
        "archive-payload-hash",
        "tools/verify_witness_archive.py",
        "if hashlib.sha256(bundle.read(name)).hexdigest() != digest:",
        "if False:",
        "tests/test_witness_archive.py::test_payload_mutation_is_rejected",
    ),
    (
        "ledger-key-pin",
        "tools/verify_triad_ledger.py",
        "if hashlib.sha256(key).hexdigest() != trusted_key_sha256:",
        "if False:",
        "tests/test_triad_multiblock.py::test_truncation_and_fully_resigned_rewrite_fail",
    ),
    (
        "ledger-head-pin",
        "tools/verify_triad_ledger.py",
        'if events[-1]["event_hash"] != expected_head:',
        "if False:",
        "tests/test_triad_multiblock.py::test_truncation_and_fully_resigned_rewrite_fail",
    ),
    (
        "ledger-chain-integrity",
        "tools/verify_triad_ledger.py",
        "events = verify_chain(events)",
        "events = events",
        "tests/test_triad_multiblock.py::test_three_events_and_middle_byte_tamper",
    ),
    (
        "receipt-ledger-head-guard",
        "packages/runtime/weaver_runtime/ledger.py",
        "if count != length or actual != expected:",
        "if False:",
        "tests/ledger/test_receipt_ledger.py::test_refuses_to_extend_when_head_row_is_rewound",
    ),
    (
        "receipt-ledger-rollback",
        "packages/runtime/weaver_runtime/ledger.py",
        '                self._conn.execute("ROLLBACK")\n'
        "                raise\n"
        "        return receipt",
        '                self._conn.execute("COMMIT")\n'
        "                raise\n"
        "        return receipt",
        "tests/ledger/test_receipt_ledger.py::test_failure_inside_transaction_rolls_back",
    ),
    (
        "receipt-ledger-sequence-owner",
        "packages/runtime/weaver_runtime/ledger.py",
        "sequence=head.length,",
        "sequence=0,",
        "tests/ledger/test_receipt_ledger.py::test_append_assigns_sequence_and_links",
    ),
    (
        "ledger-verifier-link",
        "packages/verifier/weaver_verifier/ledger.py",
        "if receipt.predecessor_digest != previous:",
        "if False:",
        "tests/ledger/test_ledger_adversarial.py::test_T3_local_reseal_breaks_downstream_link",
    ),
    (
        "ledger-verifier-canonical-bytes",
        "packages/verifier/weaver_verifier/ledger.py",
        "if not is_canonical(event_bytes):",
        "if False:",
        "tests/ledger/test_ledger_adversarial.py::test_X2_non_canonical_event_bytes_rejected_even_with_matching_digest",
    ),
    (
        "ledger-verifier-event-digest",
        "packages/verifier/weaver_verifier/ledger.py",
        "if receipt.event_digest != hashlib.sha256(event_bytes).hexdigest():",
        "if False:",
        "tests/ledger/test_ledger_adversarial.py::test_T2_payload_edit_detected",
    ),
    (
        "ledger-verifier-anchor-length",
        "packages/verifier/weaver_verifier/ledger.py",
        "if got.length != want.length:",
        "if False:",
        "tests/ledger/test_ledger_adversarial.py::test_T11_anchor_detects_truncation",
    ),
    (
        "ledger-verifier-root",
        "packages/verifier/weaver_verifier/ledger.py",
        "if receipt.root != root:",
        "if False:",
        "tests/ledger/test_ledger_adversarial.py::test_X3_rejection_cannot_be_moved_onto_authority_root",
    ),
    (
        "crypto-signature",
        "packages/verifier/weaver_verifier/crypto.py",
        "            if not verify_signature(",
        "            if False and not verify_signature(",
        "tests/triadic_controls/test_crypto_verifier.py::test_invalid_signature_does_not_poison_replay_cache",
    ),
    (
        "crypto-replay-record",
        "packages/verifier/weaver_verifier/crypto.py",
        "            if not self.replay_cache.check_and_record(",
        "            if False and not self.replay_cache.check_and_record(",
        "tests/triadic_controls/test_crypto_verifier.py::test_valid_envelope_then_replay_detected",
    ),
    (
        "crypto-registry-root-signature",
        "packages/verifier/weaver_verifier/crypto.py",
        "if root_public_key_b64url is not None and not verify_registry_root_signature(",
        "if False and not verify_registry_root_signature(",
        "tests/triadic_controls/test_registry_root_signature.py::test_tampered_registry_rejected_after_root_signature",
    ),
    (
        "crypto-quorum",
        "packages/verifier/weaver_verifier/crypto.py",
        "        if not verify_quorum(verified_groups, requested_level):",
        "        if False:",
        # Asserts INSUFFICIENT_QUORUM for a single-signer level-4 request.
        "tests/triadic_controls/test_crypto_verifier.py::test_valid_envelope_then_replay_detected",
    ),
    (
        "triad-ledger-append-lock",
        "triadic_controls/ledger.py",
        "            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)",
        "            pass",
        "tests/test_triad_ledger_concurrency.py::test_interleaved_writers_cannot_both_append",
    ),
    (
        "receipt-ledger-unique-key",
        "packages/runtime/weaver_runtime/ledger.py",
        "                    self._claim_unique_key(unique_key, receipt)",
        "                    pass",
        "tests/ledger/test_receipt_ledger.py::test_unique_key_is_enforced_across_instances",
    ),
    (
        "state-chain-validation",
        "packages/verifier/weaver_verifier/state.py",
        "    if not verdict.ok:",
        "    if False:",
        "tests/state/test_state_controls.py::test_altered_event_is_refused",
    ),
    (
        "state-reconstruction",
        "packages/verifier/weaver_verifier/state.py",
        '    return {"projection": PROJECTION, "executions": executions}',
        '    return {"projection": PROJECTION, "executions": {}}',
        "tests/state/test_state_controls.py::test_state_is_rebuilt_from_committed_events_only",
    ),
    (
        "state-source-binding",
        "packages/verifier/weaver_verifier/state.py",
        '"source": {"kind": "reducer_module_sha256", "value": REDUCER_SOURCE_SHA256},',
        '"source": {"kind": "reducer_module_sha256", "value": "unbound"},',
        "tests/state/test_state_controls.py::test_digest_binds_the_reducer_source",
    ),
    (
        "state-digest-comparison",
        "packages/verifier/weaver_verifier/state.py",
        "    if expected_digest is not None and expected_digest != digest:",
        "    if False:",
        "tests/state/test_state_controls.py::test_expected_digest_mismatch_is_refused",
    ),
    (
        "state-duplicate-commit",
        "packages/verifier/weaver_verifier/state.py",
        "        if proposal_id in executions:",
        "        if False:",
        "tests/state/test_state_controls.py::test_duplicate_commit_is_refused",
    ),
    (
        "state-claim-comparison",
        "packages/verifier/weaver_verifier/state.py",
        "        if claimed != canonicalize(state):",
        "        if False:",
        "tests/state/test_state_controls.py::test_negative_control[C7]",
    ),
    (
        "commit-boundary-gate-guard-unwired",
        "packages/runtime/weaver_runtime/gate.py",
        "                    guard=commit_guard,",
        "                    guard=None,",
        "tests/gate/test_commit_boundary.py::test_veto_recorded_in_the_ledger_before_commit_aborts",
    ),
    (
        "vertical-signer-check-unwired",
        "packages/runtime/weaver_runtime/protected_write.py",
        "            self._public_key.verify(signature_bytes, GRANT_DOMAIN + canonicalize(grant))",
        "            pass  # signature check deliberately bypassed",
        "tests/vertical/test_protected_write.py::test_v003_untrusted_issuer_key_is_refused",
    ),
    (
        "vertical-atomic-effect-unwired",
        "packages/runtime/weaver_runtime/gate.py",
        "                if self._atomic_effect is not None:",
        "                if False and self._atomic_effect is not None:",
        "tests/vertical/test_protected_write.py::test_v001_valid_signed_bound_write_and_receipt",
    ),
    (
        "vertical-owner-resource-write-skipped",
        "packages/runtime/weaver_runtime/protected_write.py",
        '        conn.execute(\n            "INSERT INTO protected_kv',
        ('        return  # no protected resource effect\n'
         '        conn.execute(\n            "INSERT INTO protected_kv'),
        "tests/vertical/test_protected_write.py::test_v001_valid_signed_bound_write_and_receipt",
    ),
    (
        "commit-boundary-ledger-guard-skipped",
        "packages/runtime/weaver_runtime/ledger.py",
        "                    guard(self._conn)",
        "                    pass",
        "tests/gate/test_commit_boundary.py::test_revocation_recorded_in_the_ledger_before_commit_aborts",
    ),
    (
        "veto-twin-threshold",
        "packages/runtime/weaver_runtime/veto.py",
        "            if trigger_in or threat_level >= THREAT_THRESHOLD:",
        "            if trigger_in or threat_level > THREAT_THRESHOLD:",
        "tests/hardware/test_veto_twin.py::test_threshold_is_191",
    ),
    (
        "veto-twin-irreversible",
        "packages/runtime/weaver_runtime/veto.py",
        "            self.status_led = 1\n            self.latch_state = 1",
        "            self.status_led = 1\n            self.latch_state = trigger_in",
        "tests/hardware/test_veto_twin.py::test_triggered_is_irreversible_without_reset",
    ),
    (
        "gate-revalidate-live",
        "packages/runtime/weaver_runtime/gate.py",
        '                self._check_live(expires_at, stage="REVALIDATE")',
        "                pass",
        "tests/gate/test_execution_gate.py::test_veto_tripping_during_execution_aborts_before_commit",
    ),
    (
        "gate-reauthorize",
        "packages/runtime/weaver_runtime/gate.py",
        "        if isinstance(again, str) or not again.allowed:",
        "        if isinstance(again, str):",
        "tests/gate/test_execution_gate.py::test_revocation_between_authorize_and_commit_aborts[REVOKED]",
    ),
    (
        "gate-checkpoint-reauthorize",
        "packages/runtime/weaver_runtime/gate.py",
        '        self._gate._check_still_authorized(self.proposal, stage="CHECKPOINT")',
        "        pass",
        "tests/gate/test_execution_gate.py::"
        "test_revocation_mid_action_is_caught_at_the_next_checkpoint",
    ),
    (
        "gate-evaluating-is-veto",
        "packages/runtime/weaver_runtime/gate.py",
        "return self._twin.current_state != STATE_ARMED or self._twin.veto_signal == 1",
        "return self._twin.veto_signal == 1",
        "tests/gate/test_execution_gate.py::test_observe_comes_before_authorize",
    ),
    (
        "gate-replay-guard",
        "packages/runtime/weaver_runtime/gate.py",
        "            if pid in self._committed:",
        "            if False:",
        "tests/gate/test_execution_gate.py::test_committed_proposal_cannot_run_again_even_after_restart",
    ),
    (
        "gate-proposal-pin-check",
        "packages/runtime/weaver_runtime/gate.py",
        "        if _canonical_or_none(proposal) != pinned.canonical:",
        "        if False:",
        "tests/gate/test_proposal_integrity.py::"
        "test_frozen_field_bypass_by_the_action_aborts_and_records_the_submitted_proposal[action]",
    ),
    (
        "proposal-payload-read-only",
        "packages/contracts/weaver_contracts/gate.py",
        '        object.__setattr__(self, "payload", _read_only(parsed))',
        '        object.__setattr__(self, "payload", parsed)',
        "tests/gate/test_proposal_integrity.py::test_proposal_payload_cannot_be_mutated_in_place[set-top]",
    ),
    # Step 7 custody (wx-checkpoint-1): prefix check, pinned keys, signatures, split
    # view, and the witness's refusal path.
    (
        "custody-prefix-regressed",
        "packages/verifier/weaver_verifier/checkpoint.py",
        "        if len(chain) < want.length:",
        "        if False:",
        "tests/custody/test_acceptance.py::test_a7_truncation_after_a_signed_checkpoint_is_refused",
    ),
    (
        "custody-prefix-forked",
        "packages/verifier/weaver_verifier/checkpoint.py",
        "        if 0 < want.length <= len(chain) and chain[want.length - 1] != want.head:",
        "        if False:",
        "tests/custody/test_acceptance.py"
        "::test_a2_full_recompute_after_a_signed_checkpoint_is_refused_as_a_fork",
    ),
    (
        "custody-pinned-key",
        "packages/verifier/weaver_verifier/checkpoint.py",
        "    if key is None:",
        "    if False:",
        "tests/custody/test_acceptance.py::test_a5_checkpoint_from_an_unpinned_key_is_rejected",
    ),
    (
        "custody-signature",
        "packages/verifier/weaver_verifier/checkpoint.py",
        "        key.verify(checkpoint.signature, statement.signing_bytes())",
        "        pass  # intentionally disabled by mutation probe",
        "tests/custody/test_acceptance.py"
        "::test_a6_attacker_signing_as_a_pinned_witness_fails_the_signature",
    ),
    (
        "custody-split-view",
        "packages/verifier/weaver_verifier/checkpoint.py",
        "            if seen != head.head:",
        "            if False:",
        "tests/custody/test_acceptance.py::test_split_view_between_witnesses_is_refused",
    ),
    (
        "witness-fork-refusal",
        "packages/witness/weaver_witness/witness.py",
        "            if problem is not None:",
        "            if False:",
        "tests/custody/test_acceptance.py"
        "::test_a4_witness_refuses_a_forked_state_and_logs_the_refusal",
    ),
    # WVR-009 registry rollback protection: the comparison and its wiring.
    (
        "registry-rollback-comparison",
        "packages/contracts/weaver_contracts/registry_sequence.py",
        "    if sequence < stored_sequence:",
        "    if False:",
        "tests/triadic_controls/test_registry_rollback.py"
        "::test_rollback_cannot_reactivate_a_revoked_key[memory]",
    ),
    (
        "registry-sequence-unwired",
        "packages/verifier/weaver_verifier/crypto.py",
        "            _advance_registry_sequence(key_registry, registry_sequence_store)",
        "            pass",
        "tests/triadic_controls/test_registry_rollback.py"
        "::test_rollback_cannot_reactivate_a_revoked_key[sqlite]",
    ),
    (
        "signing-policy-unwired",
        "packages/verifier/weaver_verifier/crypto.py",
        "        if policy_failure is not None:",
        "        if False:",
        "tests/triadic_controls/test_signing_policy.py"
        "::test_authority_token_signed_under_the_refusal_domain_is_refused",
    ),
    (
        "signing-version-pairing",
        "packages/contracts/weaver_contracts/signing_policy.py",
        "    if payload_schema_version not in versions:",
        "    if False:",
        "tests/triadic_controls/test_signing_policy.py::test_version_confusion_is_refused",
    ),
    (
        "signing-malformed-guard",
        "packages/contracts/weaver_contracts/signing_policy.py",
        "    return isinstance(value, str) and bool(value)",
        "    return True",
        "tests/triadic_controls/test_signing_policy.py"
        "::test_malformed_signing_fields_are_refused_with_a_result",
    ),
]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    baseline = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_witness_archive.py",
            "tests/test_triad_multiblock.py",
            "tests/ledger",
            "tests/triadic_controls",
            "tests/test_triad_ledger_concurrency.py",
            "tests/hardware",
            "tests/gate",
            "tests/state",
            "tests/custody",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if baseline.returncode:
        print(baseline.stdout + baseline.stderr)
        raise SystemExit("mutation baseline failed")

    results = []
    for name, filename, old, new, test in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="weaver-mutation-") as directory:
            checkout = Path(directory) / "repo"
            shutil.copytree(
                root,
                checkout,
                ignore=shutil.ignore_patterns(
                    ".git",
                    "__pycache__",
                    ".pytest_cache",
                    ".ruff_cache",
                    ".mypy_cache",
                    "build",
                    "dist",
                ),
            )
            target = checkout / filename
            source = target.read_text()
            if source.count(old) != 1:
                raise SystemExit(f"mutation anchor changed: {name}")
            target.write_text(source.replace(old, new, 1))
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", test],
                cwd=checkout,
                capture_output=True,
                text=True,
                timeout=60,
            )
            # Collection failures and crashes do not count as detected mutations.
            killed = result.returncode == 1 and "FAILED " in result.stdout
            killed = killed and "ERROR " not in result.stdout
            results.append(
                {
                    "mutation": name,
                    "detected": killed,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
    print(json.dumps({"schema": "weaver-verifier-mutations-1", "results": results}, indent=2))
    raise SystemExit(0 if all(result["detected"] for result in results) else 1)


if __name__ == "__main__":
    main()
