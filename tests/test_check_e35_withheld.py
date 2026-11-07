"""P0-009 false-green regression: process failure must not impersonate E3.5 HOLD."""

from __future__ import annotations

import subprocess

import pytest

from tools.check_e35_withheld import E35_REQUIRED, LOCAL_REQUIRED, classify


def outcome(code: int, markers: tuple[str, ...], stderr: str = ""):
    return subprocess.CompletedProcess(
        args=["synthetic"], returncode=code, stdout="\n".join(markers) + "\n", stderr=stderr
    )


def valid_local():
    return outcome(0, LOCAL_REQUIRED)


def valid_e35():
    return outcome(1, E35_REQUIRED)


def test_positive_and_negative_controls_both_needed():
    assert classify(valid_local(), valid_e35()) == []


@pytest.mark.parametrize(
    ("code", "out", "stderr"),
    [
        (1, (), "ModuleNotFoundError: No module named 'jsonschema'"),
        (1, (), "Traceback: unrelated failure"),
        (2, E35_REQUIRED, ""),
        (0, E35_REQUIRED, ""),
        (1, E35_REQUIRED[:-1], ""),
        (1, E35_REQUIRED, "warning: unreviewed stderr"),
    ],
)
def test_false_green_e35_failures_refused(code, out, stderr):
    assert classify(valid_local(), outcome(code, out, stderr))


@pytest.mark.parametrize(
    ("code", "out", "stderr"),
    [
        (1, LOCAL_REQUIRED, ""),
        (0, LOCAL_REQUIRED[:-1], ""),
        (0, LOCAL_REQUIRED, "Traceback (failure)"),
        (0, LOCAL_REQUIRED + ("RESULT: E3.5_WITHHELD",), ""),
    ],
)
def test_local_spine_cannot_fake_positive_control(code, out, stderr):
    assert classify(outcome(code, out, stderr), valid_e35())


def test_multiple_e35_results_refused():
    assert classify(valid_local(), outcome(1, E35_REQUIRED + ("RESULT: LOCAL_SPINE_VERIFIED",)))
