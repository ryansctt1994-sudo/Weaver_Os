from pathlib import Path

from tools.check_trust_domains import ROOT, check, main


def _write(root: Path, rel: str, text: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _tree(root: Path) -> None:
    _write(root, "packages/contracts/wx_contracts/__init__.py", "import json\n")
    _write(root, "packages/runtime/wx_runtime/__init__.py", "from wx_contracts import x\n")
    _write(root, "packages/verifier/wx_verifier/__init__.py", "import wx_contracts\n")


def _rules(violations):
    return [v.rule for v in violations]


def test_repository_passes_today():
    violations, _ = check(ROOT)
    assert violations == []
    assert main(["--root", str(ROOT)]) == 0


def test_absent_packages_dir_passes(tmp_path):
    assert check(tmp_path) == ([], 0)


def test_allowed_imports_pass(tmp_path):
    _tree(tmp_path)
    violations, count = check(tmp_path)
    assert violations == []
    assert count == 3


def test_verifier_importing_runtime_is_rejected(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "packages/verifier/wx_verifier/bad.py", "from wx_runtime import ledger\n")
    assert _rules(check(tmp_path)[0]) == ["FORBIDDEN_DOMAIN_IMPORT"]


def test_contracts_importing_anything_internal_is_rejected(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "packages/contracts/wx_contracts/bad.py", "import wx_verifier\n")
    assert _rules(check(tmp_path)[0]) == ["FORBIDDEN_DOMAIN_IMPORT"]


def test_package_path_form_is_resolved(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "packages/runtime/wx_runtime/bad.py", "import packages.verifier.wx_verifier\n")
    assert _rules(check(tmp_path)[0]) == ["FORBIDDEN_DOMAIN_IMPORT"]


def test_dynamic_import_is_caught(tmp_path):
    _tree(tmp_path)
    _write(
        tmp_path,
        "packages/verifier/wx_verifier/bad.py",
        "import importlib\nimportlib.import_module('wx_runtime')\n",
    )
    assert _rules(check(tmp_path)[0]) == ["FORBIDDEN_DOMAIN_IMPORT"]


def test_non_runtime_zone_import_is_rejected(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "packages/runtime/wx_runtime/bad.py", "from research.notes import idea\n")
    assert _rules(check(tmp_path)[0]) == ["NON_RUNTIME_IMPORT"]


def test_unknown_domain_fails_closed(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "packages/sidecar/thing.py", "")
    assert _rules(check(tmp_path)[0]) == ["UNKNOWN_DOMAIN"]


def test_unparseable_file_fails_closed(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "packages/runtime/wx_runtime/broken.py", "def (:\n")
    assert _rules(check(tmp_path)[0]) == ["UNPARSEABLE"]


def test_learning_may_use_runtime_but_not_verifier(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "packages/learning/wx_learning/__init__.py", "import wx_runtime\n")
    assert check(tmp_path)[0] == []
    _write(tmp_path, "packages/learning/wx_learning/bad.py", "import wx_verifier\n")
    assert _rules(check(tmp_path)[0]) == ["FORBIDDEN_DOMAIN_IMPORT"]


def test_witness_may_use_verifier_but_never_runtime(tmp_path):
    # GD-0005 D14: a witness checks what it signs with read-only code and must not
    # be able to reach the operator's ledger.
    _tree(tmp_path)
    _write(
        tmp_path,
        "packages/witness/wx_witness/__init__.py",
        "import cryptography\nimport wx_contracts\nimport wx_verifier\n",
    )
    assert check(tmp_path)[0] == []
    _write(tmp_path, "packages/witness/wx_witness/bad.py", "from wx_runtime import ledger\n")
    assert _rules(check(tmp_path)[0]) == ["FORBIDDEN_DOMAIN_IMPORT"]


# --- step 4 extensions ------------------------------------------------------


def test_contracts_must_be_stdlib_only(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "packages/contracts/wx_contracts/bad.py", "import jsonschema\n")
    assert _rules(check(tmp_path)[0]) == ["NON_STDLIB_IMPORT"]


def test_verifier_may_use_third_party_libraries(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "packages/verifier/wx_verifier/ok.py", "import cryptography\nimport json\n")
    assert check(tmp_path)[0] == []


def test_contracts_cannot_do_io(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "packages/contracts/wx_contracts/bad.py", "import sqlite3\n")
    assert _rules(check(tmp_path)[0]) == ["IO_CAPABLE_IMPORT"]


def test_verifier_cannot_spawn_processes_or_open_databases(tmp_path):
    _tree(tmp_path)
    _write(
        tmp_path,
        "packages/verifier/wx_verifier/bad.py",
        "import subprocess\nfrom sqlite3 import connect\nimport urllib.request\n",
    )
    assert _rules(check(tmp_path)[0]) == ["IO_CAPABLE_IMPORT"] * 3


def test_runtime_may_open_databases(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "packages/runtime/wx_runtime/ok.py", "import sqlite3\n")
    assert check(tmp_path)[0] == []


def test_new_legacy_canonicalizer_is_rejected(tmp_path):
    _tree(tmp_path)
    _write(
        tmp_path,
        "packages/runtime/wx_runtime/bad.py",
        "import json\ndigest = json.dumps({}, sort_keys=True)\n",
    )
    assert _rules(check(tmp_path)[0]) == ["LEGACY_CANONICALIZER"]


def test_aliased_json_dumps_is_caught(tmp_path):
    _tree(tmp_path)
    _write(
        tmp_path,
        "packages/runtime/wx_runtime/bad.py",
        "from json import dumps as d\nx = d({}, sort_keys=True)\n",
    )
    assert _rules(check(tmp_path)[0]) == ["LEGACY_CANONICALIZER"]


def test_display_json_without_sort_keys_is_allowed(tmp_path):
    _tree(tmp_path)
    _write(
        tmp_path,
        "packages/runtime/wx_runtime/ok.py",
        "import json\nprint(json.dumps({}, indent=2))\n",
    )
    assert check(tmp_path)[0] == []


def test_allowlisted_legacy_canonicalizer_passes_and_stale_entry_fails(tmp_path):
    _tree(tmp_path)
    path = "packages/verifier/weaver_verifier/crypto.py"
    _write(tmp_path, path, "import json\nx = json.dumps({}, sort_keys=True)\n")
    assert check(tmp_path)[0] == []
    _write(tmp_path, path, "x = 1\n")
    assert _rules(check(tmp_path)[0]) == ["STALE_ALLOWLIST"]
