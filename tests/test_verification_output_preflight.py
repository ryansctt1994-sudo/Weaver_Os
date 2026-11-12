"""P0 output isolation: stale evidence cannot contaminate a new verifier run."""

from pathlib import Path

import pytest

from tools.verify_all import prepare_output_workspace


def test_new_workspace_is_admitted(tmp_path: Path) -> None:
    output = tmp_path / "new-output"
    assert prepare_output_workspace(output)
    assert output.is_dir()
    assert list(output.iterdir()) == []


def test_empty_workspace_is_admitted(tmp_path: Path) -> None:
    assert prepare_output_workspace(tmp_path)


def test_ci_install_log_is_the_only_allowed_preexisting_file(tmp_path: Path) -> None:
    (tmp_path / "install.log").write_text("dependency log\n")
    assert prepare_output_workspace(tmp_path)


@pytest.mark.parametrize(
    "stale",
    [
        "verification-report.json",
        "evidence-manifest.json",
        "adversarial-results.json",
        "unit_and_integration--run.log",
        "unexpected.txt",
    ],
)
def test_preexisting_evidence_or_unexpected_file_refused(
    tmp_path: Path, stale: str
) -> None:
    (tmp_path / stale).write_text("old\n")
    assert not prepare_output_workspace(tmp_path)


def test_install_log_directory_refused(tmp_path: Path) -> None:
    (tmp_path / "install.log").mkdir()
    assert not prepare_output_workspace(tmp_path)


def test_workspace_regular_file_refused(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.write_text("not a directory\n")
    assert not prepare_output_workspace(output)


def test_preexisting_symlink_refused(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "output-link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    assert not prepare_output_workspace(link)


def test_symlink_install_log_refused(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_text("outside\n")
    link = tmp_path / "install.log"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    assert not prepare_output_workspace(tmp_path)
