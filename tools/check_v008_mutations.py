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
UNIT = "tests/test_owner_ipc.py"

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
    baseline = _pytest([ISOLATION, UNIT], root, env)
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
