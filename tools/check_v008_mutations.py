"""Require targeted removals of the V008 isolation controls to be detected by tests.

Companion to tools/check_verifier_mutations.py. The V008 acceptance tests start a real
owner under other uids, so this runner needs root and refuses to run without it: a skipped
test must never be counted as a detected mutation. Run it as root with
WEAVER_REQUIRE_ISOLATION=1 (set for the child processes here).

Research-only. It shows that the listed tests fail when the listed control is removed; it
does not show the controls are sufficient.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ISOLATION = "tests/isolation/test_v008_isolated_owner.py"
CRASH = "tests/isolation/test_v008_crash_recovery.py"
DEADLINES = "tests/isolation/test_v008_request_deadlines.py"
TELEMETRY = "tests/isolation/test_v008_edge_telemetry.py"
JSON_DEPTH = "tests/isolation/test_v008_json_depth.py"
UNIT = "tests/test_owner_ipc.py"
OUTCOME_UNIT = "tests/test_owner_outcome.py"
DEADLINE_UNIT = "tests/test_owner_deadlines.py"
TELEMETRY_UNIT = "tests/test_owner_telemetry.py"

MUTATIONS = [
    (
        "v008-peer-allowlist-skipped",
        "packages/runtime/weaver_runtime/owner_service.py",
        "        actors = self._peers.get(creds.uid)\n",
        '        actors = self._peers.get(creds.uid, frozenset({"agent-a"}))\n',
        f"{ISOLATION}::test_valid_grant_from_an_unlisted_uid_is_refused_and_owner_keeps_serving",
    ),
    (
        "v008-actor-binding-skipped",
        "packages/runtime/weaver_runtime/owner_service.py",
        "        if proposal.actor_id not in actors:",
        "        if False:",
        f"{ISOLATION}::test_listed_uid_cannot_speak_for_an_unlisted_actor",
    ),
    (
        "v008-client-peer-check-skipped",
        "packages/runtime/weaver_runtime/owner_ipc.py",
        "            if creds.uid != self._owner_uid:",
        "            if False:",
        f"{ISOLATION}::test_client_sends_nothing_to_a_server_running_as_the_wrong_uid",
    ),
    (
        "v008-path-trust-disabled",
        "packages/runtime/weaver_runtime/owner_ipc.py",
        "    absolute = Path(os.path.abspath(os.fspath(path)))\n",
        "    return\n    absolute = Path(os.path.abspath(os.fspath(path)))\n",
        f"{ISOLATION}::test_client_refuses_a_socket_in_a_directory_an_attacker_controls",
    ),
    (
        "v008-symlink-check-skipped",
        "packages/runtime/weaver_runtime/owner_ipc.py",
        "        if stat.S_ISLNK(st.st_mode):",
        "        if False:",
        f"{ISOLATION}::test_owner_refuses_a_symlinked_data_directory",
    ),
    (
        "v008-inherited-descriptor-check-skipped",
        "packages/runtime/weaver_runtime/owner_main.py",
        "    extra = [fd for fd in _open_descriptors() if fd > 2]",
        "    extra = []",
        f"{ISOLATION}::test_owner_refuses_to_start_with_an_inherited_descriptor",
    ),
    (
        "v008-dumpable-not-cleared",
        "packages/runtime/weaver_runtime/owner_main.py",
        "    _set_non_dumpable()\n    config = _load_config(config_path)",
        "    config = _load_config(config_path)",
        f"{ISOLATION}::test_owner_runs_as_its_own_uid_and_is_marked_non_dumpable",
    ),
    (
        "v008-root-refusal-removed",
        "packages/runtime/weaver_runtime/owner_main.py",
        "    if os.geteuid() == 0:",
        "    if False:",
        f"{ISOLATION}::test_owner_refuses_to_run_as_root",
    ),
    (
        "v008-config-trust-check-removed",
        "packages/runtime/weaver_runtime/owner_main.py",
        '    assert_trusted_path(path, os.geteuid(), leaf="private_file")',
        "    pass",
        f"{ISOLATION}::test_owner_refuses_a_substituted_or_loosened_config",
    ),
    (
        "v008-unknown-config-fields-allowed",
        "packages/runtime/weaver_runtime/owner_main.py",
        "    if not _REQUIRED <= keys or keys - _REQUIRED - _OPTIONAL:",
        "    if not _REQUIRED <= keys:",
        f"{ISOLATION}::test_owner_refuses_a_config_with_unknown_fields",
    ),
    (
        "v008-database-owner-check-removed",
        "packages/runtime/weaver_runtime/owner_main.py",
        "            or st.st_uid != os.geteuid()\n",
        "            or False\n",
        f"{ISOLATION}::test_owner_refuses_a_database_file_it_does_not_own",
    ),
    (
        "v008-socket-directory-check-removed",
        "packages/runtime/weaver_runtime/owner_service.py",
        '        assert_trusted_path(parent, os.geteuid(), leaf="public_dir")',
        "        pass",
        f"{ISOLATION}::test_owner_refuses_a_socket_directory_others_can_write",
    ),
    (
        "v008-data-directory-check-removed",
        "packages/runtime/weaver_runtime/owner_main.py",
        '    assert_trusted_path(data_dir, os.geteuid(), leaf="private_dir")',
        "    pass",
        f"{ISOLATION}::test_owner_refuses_a_data_directory_others_can_enter",
    ),
    (
        "v008-frame-size-limit-removed",
        "packages/runtime/weaver_runtime/owner_ipc.py",
        "    if length == 0 or length > MAX_FRAME_BYTES:",
        "    if length == 0:",
        f"{UNIT}::test_oversized_zero_and_truncated_frames_are_refused",
    ),
    (
        "v008-duplicate-key-check-removed",
        "packages/runtime/weaver_runtime/owner_ipc.py",
        '            raise FrameError(f"duplicate key {key!r}")',
        "            pass",
        f"{UNIT}::test_strict_json_refuses_ambiguous_or_invalid_text",
    ),
    # Crash-recovery slice: outcome lookup, retry identity and ambiguity handling.
    (
        "v008r-outcome-ignores-commits",
        "packages/runtime/weaver_runtime/owner_outcome.py",
        "    if commits:\n",
        "    if False:\n",
        f"{CRASH}::test_owner_killed_after_commit_before_reply_keeps_one_effect_and_its_receipt",
    ),
    (
        "v008r-multiple-commit-guard-removed",
        "packages/runtime/weaver_runtime/owner_outcome.py",
        "    if commits_seen > 1:",
        "    if False:",
        f"{OUTCOME_UNIT}::test_two_commits_for_one_proposal_id_are_reported_as_inconsistent",
    ),
    (
        "v008r-digest-conflict-check-skipped",
        "packages/runtime/weaver_runtime/owner_outcome.py",
        "        if submitted_sha256 is not None"
        " and proposal_digest(proposal) != submitted_sha256:",
        "        if False:",
        f"{CRASH}::test_same_id_with_different_content_is_a_conflict_never_a_commit",
    ),
    (
        "v008r-client-conflict-check-skipped",
        "packages/runtime/weaver_runtime/owner_ipc.py",
        '            and found.get("proposal_sha256") != proposal_digest(body)',
        "            and False",
        f"{OUTCOME_UNIT}::test_client_reports_a_commit_of_different_content_as_conflict",
    ),
    (
        "v008r-lost-reply-reported-as-refusal",
        "packages/runtime/weaver_runtime/owner_ipc.py",
        '                    raise OutcomeUnknown(f"no reply after sending: {exc}") from exc',
        '                    return {"ok": True, "status": "REJECTED",'
        ' "outcome": {"status": "REFUSED"}}',
        f"{OUTCOME_UNIT}::test_lost_reply_after_sending_is_outcome_unknown_not_refusal",
    ),
    (
        "v008r-unreachable-owner-reported-as-unknown",
        "packages/runtime/weaver_runtime/owner_ipc.py",
        '                raise OwnerUnavailable(f"cannot connect to the owner: {exc}") from exc',
        '                raise OutcomeUnknown(f"cannot connect to the owner: {exc}") from exc',
        f"{CRASH}::test_owner_killed_inside_the_commit_transaction_leaves_no_effect",
    ),
    (
        "v008r-outcome-not-actor-scoped",
        "packages/runtime/weaver_runtime/owner_outcome.py",
        '            if proposal.get("actor_id") not in actors:\n',
        "            if False:\n",
        f"{CRASH}::test_another_actors_later_refusal_neither_leaks_nor_hides_your_own_record",
    ),
    (
        "v008r-authorised-conflict-signal-ignored",
        "packages/runtime/weaver_runtime/owner_outcome.py",
        '    if any(receipt.get("reason_code") == _TAKEN for _, receipt in refusals):',
        "    if False:",
        f"{CRASH}::"
        "test_an_authorised_attempt_on_an_id_another_actor_committed_is_a_final_conflict",
    ),
    (
        "v008r-unknown-failpoint-accepted",
        "packages/runtime/weaver_runtime/owner_main.py",
        "    if failpoint and failpoint not in _FAILPOINTS:",
        "    if False:",
        f"{CRASH}::test_unknown_failpoint_refuses_to_start",
    ),
    (
        "v008r-failpoint-opt-in-skipped",
        "packages/runtime/weaver_runtime/owner_main.py",
        "    if failpoint and not enabled:",
        "    if False:",
        f"{CRASH}::test_a_failpoint_cannot_be_armed_unless_the_owner_config_opts_in",
    ),
    (
        "v008r-ledger-unique-key-claim-removed",
        "packages/runtime/weaver_runtime/ledger.py",
        "                if unique_key is not None:\n"
        "                    self._claim_unique_key(unique_key, receipt)",
        "                if False:\n"
        "                    self._claim_unique_key(unique_key, receipt)",
        f"{CRASH}::test_a_true_race_between_two_owners_is_settled_by_the_ledger_unique_key",
    ),
    # Request deadlines: one connection may hold the single-request owner only so long.
    (
        "v008d-receive-deadline-not-applied",
        "packages/runtime/weaver_runtime/owner_ipc.py",
        "            sock.settimeout(_time_left(deadline))  # absolute: progress never extends it",
        "            pass",
        f"{DEADLINE_UNIT}::test_a_trickling_sender_hits_the_deadline_despite_steady_progress",
    ),
    (
        "v008d-send-deadline-not-applied",
        "packages/runtime/weaver_runtime/owner_ipc.py",
        "        sock.settimeout(_time_left(deadline))  # sendall: total time, not per chunk",
        "        pass",
        f"{DEADLINE_UNIT}::test_a_peer_that_never_reads_cannot_hold_send_frame_past_its_deadline",
    ),
    (
        "v008d-service-ignores-request-deadline",
        "packages/runtime/weaver_runtime/owner_service.py",
        "            request = recv_frame(conn, deadline=deadline)",
        "            request = recv_frame(conn)",
        f"{DEADLINES}::test_a_trickling_listed_peer_cannot_hold_the_owner_beyond_the_deadline",
    ),
    (
        "v008d-service-ignores-reply-deadline",
        "packages/runtime/weaver_runtime/owner_service.py",
        "            send_frame(conn, reply, deadline=time.monotonic() + self._reply_deadline)",
        "            send_frame(conn, reply)",
        f"{DEADLINE_UNIT}::test_the_service_abandons_a_reply_its_peer_never_reads",
    ),
    (
        "v008d-size-cap-from-header-removed",
        "packages/runtime/weaver_runtime/owner_ipc.py",
        "    if length == 0 or length > MAX_FRAME_BYTES:",
        "    if length == 0:",
        f"{DEADLINES}::test_an_oversized_request_is_refused_from_its_header_and_service_continues",
    ),
    # Service-edge security telemetry: never part of a decision, bounded, kernel-attributed.
    (
        "v008t-telemetry-failure-propagates",
        "packages/runtime/weaver_runtime/owner_service.py",
        "        except Exception:\n            self.telemetry_errors += 1",
        "        except ValueError:\n            self.telemetry_errors += 1",
        f"{TELEMETRY}::test_e01_a_recorder_that_raises_never_stops_the_owner",
    ),
    (
        "v008t-recorded-before-close",
        "packages/runtime/weaver_runtime/owner_service.py",
        "            conn.close()  # close without reading a byte\n"
        "            self._note(PEER_DENIED, creds)",
        "            self._note(PEER_DENIED, creds)\n"
        "            conn.close()  # close without reading a byte",
        f"{TELEMETRY_UNIT}::test_a_slow_recorder_never_delays_closing_on_an_unlisted_peer",
    ),
    (
        "v008t-recorded-before-reply",
        "packages/runtime/weaver_runtime/owner_service.py",
        "        self._reply(conn, reply)\n        error = reply.get(\"error\")\n"
        "        edge = _EDGE_REPLIES.get(error) if isinstance(error, str) else None\n"
        "        if edge is not None:\n            self._note(edge, creds)",
        "        error = reply.get(\"error\")\n"
        "        edge = _EDGE_REPLIES.get(error) if isinstance(error, str) else None\n"
        "        if edge is not None:\n            self._note(edge, creds)\n"
        "        self._reply(conn, reply)",
        f"{TELEMETRY_UNIT}::test_a_slow_recorder_never_delays_the_reply",
    ),
    (
        "v008t-persistence-in-request-path",
        "packages/runtime/weaver_runtime/owner_telemetry.py",
        "        self._dirty.set()\n\n    def _bucket",
        "        self._flush_once()\n\n    def _bucket",
        f"{TELEMETRY}::test_e01_a_hung_telemetry_write_cannot_hold_the_owner",
    ),
    (
        "v008t-uid-cap-removed",
        "packages/runtime/weaver_runtime/owner_telemetry.py",
        "        if len(self._retained) < self._max_uids:",
        "        if True:",
        f"{TELEMETRY_UNIT}::test_uid_cardinality_cap_is_deterministic_and_never_moves_counts",
    ),
    (
        "v008t-recent-unbounded",
        "packages/runtime/weaver_runtime/owner_telemetry.py",
        "collections.deque(maxlen=max_recent)",
        "collections.deque()",
        f"{TELEMETRY_UNIT}::test_structures_stay_bounded_under_many_uids_and_events",
    ),
    (
        "v008t-saturation-removed",
        "packages/runtime/weaver_runtime/owner_telemetry.py",
        "            if row.get(event_class, 0) >= self._max_count:",
        "            if False:",
        f"{TELEMETRY_UNIT}::test_counters_saturate_deterministically_and_say_so",
    ),
    (
        "v008t-temp-file-follows-links",
        "packages/runtime/weaver_runtime/owner_telemetry.py",
        "        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC",
        "        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_CLOEXEC",
        f"{TELEMETRY_UNIT}::test_a_planted_symlink_at_the_temp_path_is_never_followed",
    ),
    (
        "v008t-file-checks-removed",
        "packages/runtime/weaver_runtime/owner_telemetry.py",
        "            or st.st_mode & 0o077\n            or st.st_nlink != 1\n",
        "            or False\n",
        f"{TELEMETRY_UNIT}::test_an_unsafe_existing_file_refuses_to_load",
    ),
    (
        "v008t-fifo-open-blocks",
        "packages/runtime/weaver_runtime/owner_telemetry.py",
        "        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC",
        "        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC",
        f"{TELEMETRY_UNIT}::test_a_planted_fifo_is_refused_without_blocking",
    ),
    (
        "v008t-reserved-uids-not-honoured",
        "packages/runtime/weaver_runtime/owner_telemetry.py",
        "        if uid in self._reserved:  # configured principals never compete for a slot",
        "        if False:",
        f"{TELEMETRY_UNIT}::test_reserved_uids_keep_dedicated_counters_when_the_cap_is_exhausted",
    ),
    (
        "v008t-fold-on-load-removed",
        "packages/runtime/weaver_runtime/owner_telemetry.py",
        "            if key == OTHER or key not in keep:",
        "            if key == OTHER:",
        f"{TELEMETRY_UNIT}::test_load_folds_dropped_uids_into_other_exactly_once_and_keeps_totals",
    ),
    (
        "v008t-degraded-not-persisted",
        "packages/runtime/weaver_runtime/owner_telemetry.py",
        '                "degraded": sorted(self._degraded),\n                "carried_over"',
        '                "carried_over"',
        f"{TELEMETRY_UNIT}::"
        "test_a_failed_snapshot_is_not_evidence_and_degradation_rides_the_next_success",
    ),
    (
        "v008t-dir-fsync-not-run",
        "packages/runtime/weaver_runtime/owner_telemetry.py",
        "            self._sync_dir()\n        except OSError:",
        "            pass\n        except OSError:",
        f"{TELEMETRY_UNIT}::test_a_failed_directory_sync_is_degraded_never_durable_success",
    ),
    (
        "v008t-dir-fsync-failure-reported-ok",
        "packages/runtime/weaver_runtime/owner_telemetry.py",
        '                self._last_persist = "unsynced"\n'
        "                self._degraded.add(DIR_FSYNC_FAILED)",
        '                self._last_persist = "ok"',
        f"{TELEMETRY_UNIT}::test_a_failed_directory_sync_is_degraded_never_durable_success",
    ),
    (
        "v008t-replace-not-directory-relative",
        "packages/runtime/weaver_runtime/owner_telemetry.py",
        "                self._tmp_name, self._name,"
        " src_dir_fd=self._dirfd, dst_dir_fd=self._dirfd\n"
        "            )\n            replaced = True",
        "                self._tmp_name, self._name\n            )\n            replaced = True",
        f"{TELEMETRY_UNIT}::test_a_swapped_parent_path_cannot_redirect_later_writes",
    ),
    (
        "v008t-identity-not-kernel",
        "packages/runtime/weaver_runtime/owner_service.py",
        "            self._telemetry.record(event_class, creds.uid, creds.pid)",
        "            self._telemetry.record(event_class, 0, 0)",
        f"{TELEMETRY}::test_e04_records_carry_the_kernel_uid_and_pid",
    ),
    # JSON nesting bound: a deep request cannot recurse the parser into crashing the owner.
    # The depth scan and the RecursionError backstop are tested apart on purpose. A single
    # very deep payload cannot tell them apart, because either control alone would refuse it;
    # so the scan is removed against a depth-33 payload (shallow enough that the parser never
    # recurses, so only the scan can catch it), and the backstop is removed against an
    # injected RecursionError on a shallow payload (which the scan admits either way).
    (
        "v008n-depth-scan-removed",
        "packages/runtime/weaver_runtime/owner_ipc.py",
        "            if depth > MAX_JSON_DEPTH:\n",
        "            if False:\n",
        f"{UNIT}::test_json_nesting_depth_32_is_accepted_and_33_is_refused",
    ),
    (
        "v008n-recursion-backstop-removed",
        "packages/runtime/weaver_runtime/owner_ipc.py",
        "    except RecursionError as exc:  # backstop if a pathological payload slips past"
        " the scan\n"
        '        raise FrameError("JSON nesting is too deep for the parser") from exc\n',
        "",
        f"{UNIT}::test_a_parser_recursion_error_is_converted_to_a_frame_error",
    ),
]

IGNORE = shutil.ignore_patterns(
    ".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "build", "dist"
)


def _pytest(args, cwd, env):
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *args],
        cwd=cwd, capture_output=True, text=True, timeout=120, env=env, check=False,
    )


def main() -> None:
    if os.geteuid() != 0:
        raise SystemExit("needs root: a skipped isolation test must not count as a detection")
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, WEAVER_REQUIRE_ISOLATION="1")
    baseline = _pytest(
        [ISOLATION, CRASH, DEADLINES, TELEMETRY, JSON_DEPTH, UNIT, OUTCOME_UNIT,
         DEADLINE_UNIT, TELEMETRY_UNIT],
        root, env,
    )
    if baseline.returncode:
        print(baseline.stdout + baseline.stderr)
        raise SystemExit("V008 mutation baseline failed")

    results = []
    for name, filename, old, new, test in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="weaver-v008-mutation-") as directory:
            os.chmod(directory, 0o755)
            checkout = Path(directory) / "repo"
            shutil.copytree(root, checkout, ignore=IGNORE)
            target = checkout / filename
            source = target.read_text()
            if source.count(old) != 1:
                raise SystemExit(f"mutation anchor changed: {name}")
            target.write_text(source.replace(old, new, 1))
            try:
                result = _pytest([test], checkout, env)
                returncode, stdout, stderr = result.returncode, result.stdout, result.stderr
            except subprocess.TimeoutExpired:
                returncode, stdout, stderr = 124, "", "timed out"
            killed = returncode == 1 and "FAILED " in stdout and "ERROR " not in stdout
            results.append(
                {
                    "mutation": name,
                    "detected": killed,
                    "returncode": returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                }
            )
    print(json.dumps({"schema": "weaver-v008-mutations-1", "results": results}, indent=2))
    raise SystemExit(0 if all(result["detected"] for result in results) else 1)


if __name__ == "__main__":
    main()
