"""Contract tests for governance.claim_audit.

Each test builds a small repository in a temporary directory, so no
deliberately overclaiming fixture files are committed anywhere.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.claim_audit import claim_audit as ca

SKILL = Path(__file__).resolve().parents[2] / "tools" / "claim_audit"

LEDGER = """# Ledger

## Blocking Rule

Any public claim using the words below is blocked until corresponding evidence exists:

```text
production-ready
validated
ASI
```
"""


def make_repo(
    tmp_path: Path, files: dict[str, str], config: dict | None = None, ledger: bool = True
) -> Path:
    root = tmp_path / "repo"
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if ledger:
        (root / "governance").mkdir(parents=True, exist_ok=True)
        (root / "governance" / "open_gap_ledger.md").write_text(LEDGER, encoding="utf-8")
    if config is not None:
        (root / "governance").mkdir(parents=True, exist_ok=True)
        (root / "governance" / "claims.json").write_text(json.dumps(config), encoding="utf-8")
    return root


def categories(report: dict, file: str | None = None) -> list[tuple[str, str]]:
    return [
        (f["term"], f["category"]) for f in report["findings"] if file is None or f["file"] == file
    ]


# --- Classification -------------------------------------------------------------


def test_terms_come_from_the_ledger_and_the_ledger_itself_passes(tmp_path):
    report = ca.audit(make_repo(tmp_path, {}))
    assert report["terms_source"] == "governance/open_gap_ledger.md"
    assert report["blocked_terms"] == ["production-ready", "validated", "ASI"]
    assert report["passed"], report["findings"]
    assert categories(report) == [
        ("production-ready", "denied"),
        ("validated", "denied"),
        ("ASI", "denied"),
    ]


def test_default_terms_without_a_ledger(tmp_path):
    report = ca.audit(make_repo(tmp_path, {"README.md": "This kit is certified.\n"}, ledger=False))
    assert report["terms_source"] == "default"
    assert ("certified", "claim") in categories(report)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("The system is production-ready.\n", "claim"),
        ("The system is not production-ready.\n", "denied"),
        ("Production-ready: no.\n", "denied"),
        ("No production-ready claim is made.\n", "denied"),
        ("It is a prototype. It is production-ready.\n", "claim"),  # negation in another sentence
        ("It is not a toy. The kernel is production-ready.\n", "claim"),
        ("A prototype rather than a production-ready service.\n", "denied"),
        ("| Production-ready | none |\n", "denied"),  # table row is one record
        ("| Status | production-ready |\n", "claim"),
        ("## Production-Ready Deployment\n", "claim"),
        ("Results were Validated by the team.\n", "claim"),
        ("Z3-validated safety checks.\n", "claim"),
        ("Accepts non-validated input.\n", "denied"),
        ("The cache was invalidated.\n", None),
    ],
)
def test_sentence_level_classification(tmp_path, text, expected):
    report = ca.audit(make_repo(tmp_path, {"README.md": text}))
    found = [c for t, c in categories(report, "README.md")]
    assert found == ([expected] if expected else []), (text, report["findings"])


def test_negation_far_from_the_term_does_not_deny_it(tmp_path):
    text = (
        "We do not ship binaries, and after many months of careful work and review "
        "the platform is now production-ready.\n"
    )
    assert categories(ca.audit(make_repo(tmp_path, {"README.md": text})), "README.md") == [
        ("production-ready", "claim")
    ]


def test_list_items_and_code_blocks_take_context_from_heading_or_lead_in(tmp_path):
    text = (
        "## Not claimed\n\n- production-ready\n- validated\n\n"
        "## Status\n\n- production-ready\n\n"
        "Blocked until evidence exists:\n\n```text\nvalidated\n```\n"
    )
    report = ca.audit(make_repo(tmp_path, {"README.md": text}))
    assert categories(report, "README.md") == [
        ("production-ready", "denied"),
        ("validated", "denied"),
        ("production-ready", "claim"),
        ("validated", "denied"),
    ]


def test_indented_code_lines_are_not_joined_into_sentences(tmp_path):
    text = "Code:\n\n    # validated input path\n    if not ready:\n        return\n"
    assert ("validated", "claim") in categories(ca.audit(make_repo(tmp_path, {"notes.md": text})))


def test_python_identifiers_are_ignored_but_strings_and_comments_are_scanned(tmp_path):
    src = (
        "validated = check(x)\n"
        "if validated:\n"
        "    pass\n"
        "# this module is production-ready\n"
        'MESSAGE = "Results validated by experts"\n'
        'def f():\n    """Not production-ready yet."""\n'
    )
    report = ca.audit(make_repo(tmp_path, {"mod.py": src}))
    assert categories(report, "mod.py") == [
        ("production-ready", "claim"),
        ("validated", "claim"),
        ("production-ready", "denied"),
    ]


def test_acronyms_are_case_sensitive_and_word_bounded(tmp_path):
    text = "An ASI system. Basic ASIN codes. Spanish: asi es.\n"
    assert categories(ca.audit(make_repo(tmp_path, {"README.md": text})), "README.md") == [
        ("ASI", "claim")
    ]


def test_terms_in_file_paths_are_claims(tmp_path):
    report = ca.audit(
        make_repo(tmp_path, {"Weaver ASI": "notes\n", "docs/validated_results.md": "x\n"})
    )
    paths = [
        (f["file"], f["category"]) for f in report["findings"] if f["category"] == "path_claim"
    ]
    assert ("Weaver ASI", "path_claim") in paths and (
        "docs/validated_results.md",
        "path_claim",
    ) in paths


def test_watch_terms_warn_but_do_not_fail(tmp_path):
    report = ca.audit(make_repo(tmp_path, {"README.md": "An immutable, tamper-proof log.\n"}))
    assert report["passed"] and report["warnings"] == 2 and report["errors"] == 0


# --- Config: backing, waivers, staleness ----------------------------------------


def test_backed_claim_with_existing_evidence_passes(tmp_path):
    config = {
        "backed_claims": [
            {
                "term": "validated",
                "file": "README.md",
                "contains": "schema is validated",
                "evidence": ["tests/test_schema.py"],
            }
        ]
    }
    root = make_repo(
        tmp_path,
        {
            "README.md": "The schema is validated in CI.\n",
            "tests/test_schema.py": "def test(): pass\n",
        },
        config,
    )
    report = ca.audit(root)
    assert report["passed"] and ("validated", "backed") in categories(report, "README.md")


def test_backed_claim_with_missing_evidence_fails(tmp_path):
    config = {
        "backed_claims": [
            {
                "term": "validated",
                "file": "README.md",
                "contains": "schema is validated",
                "evidence": ["tests/gone.py"],
            }
        ]
    }
    report = ca.audit(
        make_repo(tmp_path, {"README.md": "The schema is validated in CI.\n"}, config)
    )
    assert not report["passed"] and ("validated", "evidence_missing") in categories(
        report, "README.md"
    )


def test_waiver_passes_and_is_counted_as_debt(tmp_path):
    config = {
        "waivers": [
            {
                "term": "validated",
                "file": "*.md",
                "contains": "validated by the team",
                "reason": "historical quote",
            }
        ]
    }
    report = ca.audit(
        make_repo(tmp_path, {"README.md": "Results were validated by the team.\n"}, config)
    )
    assert report["passed"] and report["waiver_debt"] == 1


def test_waiver_matches_beyond_the_report_snippet(tmp_path):
    line = "x" * 300 + " the system is production-ready and reliable.\n"
    config = {
        "waivers": [
            {
                "term": "production-ready",
                "file": "README.md",
                "contains": "production-ready and reliable",
                "reason": "r",
            }
        ]
    }
    report = ca.audit(make_repo(tmp_path, {"README.md": line}, config))
    assert report["passed"], report["findings"]
    assert [f["category"] for f in report["findings"] if f["file"] == "README.md"] == ["waived"]


@pytest.mark.parametrize("key", ["waivers", "backed_claims"])
def test_entries_that_match_nothing_fail_as_stale(tmp_path, key):
    entry = {"term": "validated", "file": "README.md", "contains": "text that changed"}
    entry.update({"reason": "r"} if key == "waivers" else {"evidence": ["README.md"]})
    report = ca.audit(
        make_repo(tmp_path, {"README.md": "Results were validated by the team.\n"}, {key: [entry]})
    )
    assert not report["passed"]
    assert any(f["category"] == "stale_entry" for f in report["findings"])


def test_excludes_need_a_reason_and_are_applied(tmp_path):
    good = {"exclude": [{"glob": "vendor/**", "reason": "third-party copy"}]}
    assert ca.audit(make_repo(tmp_path / "a", {"vendor/x.md": "It is production-ready.\n"}, good))[
        "passed"
    ]
    with pytest.raises(ca.Refusal):
        ca.audit(make_repo(tmp_path / "b", {}, {"exclude": [{"glob": "vendor/**", "reason": " "}]}))


# --- Refusal rule ------------------------------------------------------------------


@pytest.mark.parametrize(
    "config",
    [
        {"unknown": 1},
        {"version": 2},
        {"waivers": [{"term": "validated", "file": "README.md", "contains": "x"}]},  # no reason
        {
            "backed_claims": [
                {"term": "validated", "file": "README.md", "contains": "x", "evidence": []}
            ]
        },
    ],
)
def test_malformed_config_is_refused(tmp_path, config):
    with pytest.raises(ca.Refusal):
        ca.audit(make_repo(tmp_path, {}, config))


def test_cli_exit_codes(tmp_path):
    script = [sys.executable, str(SKILL / "claim_audit.py")]
    clean = make_repo(tmp_path / "clean", {"README.md": "A prototype.\n"})
    dirty = make_repo(tmp_path / "dirty", {"README.md": "It is production-ready.\n"})
    assert subprocess.run(script + [str(clean)], capture_output=True).returncode == 0
    assert subprocess.run(script + [str(dirty)], capture_output=True).returncode == 1
    assert subprocess.run(script + [str(tmp_path / "missing")], capture_output=True).returncode == 2
    bad = make_repo(tmp_path / "bad", {}, {"version": 9})
    assert subprocess.run(script + [str(bad)], capture_output=True).returncode == 2


# --- Outputs ----------------------------------------------------------------------


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SKILL / name).read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_report_matches_output_schema_and_hash_is_deterministic(tmp_path):
    root = make_repo(
        tmp_path, {"README.md": "It is production-ready. Not validated.\n", "Weaver ASI": "x\n"}
    )
    a, b = ca.audit(root), ca.audit(root)
    assert list(_validator("outputs.schema.json").iter_errors(a)) == []
    assert a["report_hash"] == b["report_hash"]
    from tools.claim_audit.legacy_canonical import profiled_sha256

    assert (
        profiled_sha256({k: v for k, v in a.items() if k != "report_hash"}, a["hash_profile"])
        == a["report_hash"]
    )


def test_report_hash_changes_with_content(tmp_path):
    r1 = ca.audit(make_repo(tmp_path / "1", {"README.md": "It is production-ready.\n"}))
    r2 = ca.audit(make_repo(tmp_path / "2", {"README.md": "It is not production-ready.\n"}))
    assert r1["report_hash"] != r2["report_hash"]


def test_input_schema_accepts_cli_shaped_inputs():
    v = _validator("inputs.schema.json")
    assert (
        list(v.iter_errors({"root": ".", "config": None, "json": "out.json", "show_info": True}))
        == []
    )
    assert list(v.iter_errors({"config": "x"}))  # root required


def test_manifest_matches_skill_spec():
    manifest = json.loads((SKILL / "manifest.json").read_text())
    assert manifest["id"] == ca.SKILL_ID and manifest["version"] == ca.SKILL_VERSION
    assert (SKILL / manifest["entrypoint"]).is_file()


# --- This repository -----------------------------------------------------------------


def test_this_repository_passes_its_own_claim_audit():
    repo = SKILL.parents[1] / "docs" / "consolidation"
    report = ca.audit(repo)
    unhandled = [f for f in report["findings"] if f["severity"] == "error"]
    assert report["passed"], "\n".join(
        f"{f['file']}:{f['line']} {f['term']!r} {f['category']}: {f['text']}" for f in unhandled
    )


def test_empty_scan_cannot_be_counted_as_acceptance(tmp_path, capsys):
    assert ca.main([str(tmp_path), "--require-files"]) == 2
    assert "no tracked text files" in capsys.readouterr().err


def test_audit_does_not_read_a_symlinked_file_outside_its_checkout(tmp_path):
    root = make_repo(tmp_path / "local", {"README.md": "A prototype.\n"}, ledger=False)
    outside = tmp_path / "private.md"
    outside.write_text("SECRET production-ready\n")
    (root / "linked.md").symlink_to(outside)
    report = ca.audit(root)
    assert report["passed"]
    assert not any("SECRET" in item["text"] for item in report["findings"])


def test_text_read_has_a_bound_before_allocating_the_contents(tmp_path, monkeypatch):
    target = tmp_path / "file.md"
    target.write_text("A prototype.\n")
    original = Path.open

    class BoundedStream(io.BytesIO):
        def read(self, size=-1):
            assert 0 <= size <= ca.MAX_BYTES + 1, "unbounded source read"
            return super().read(size)

    def open_file(path, *args, **kwargs):
        if path == target:
            return BoundedStream(b"A prototype.\n")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_file)
    assert ca._read_text(target) == "A prototype.\n"
