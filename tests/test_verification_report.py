"""Reports cannot claim success with failed, missing, or duplicated checks."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/verification"


@pytest.mark.parametrize(
    "name", ["missing-check", "failed-check", "duplicate-check", "unknown-field"]
)
def test_invalid_report(name):
    validator = Draft202012Validator(
        json.loads((ROOT / "schemas/verification_run.schema.json").read_text())
    )
    with pytest.raises(ValidationError):
        validator.validate(json.loads((FIXTURES / f"report-{name}.json").read_text()))


def test_valid_report_and_schema_copy():
    validator = Draft202012Validator(
        json.loads((ROOT / "schemas/verification_run.schema.json").read_text())
    )
    report = json.loads((FIXTURES / "report-valid.json").read_text())
    validator.validate(report)
    failure = deepcopy(report)
    failure["status"] = "FAIL"
    failure["checks"][0].update(status="FAIL", returncode=1)
    validator.validate(failure)
    assert (ROOT / "schemas/triad_event.schema.json").read_bytes() == (
        ROOT / "triadic_controls/schemas/triad_event.schema.json"
    ).read_bytes()
