# Gate 1 Debug Update

## Current Status

Gate 1 has not achieved E3.

Latest observed status before this patch:

```text
normal tests: success
triadic-controls CI: success
Gate 1 Receipt: failure
CI: failure
E3: not claimed
```

## Observed Failure Mode

The prior `gate1-evidence` artifact uploaded successfully, but it only contained:

```text
manifests/MUST_KEEP_REGISTRY.v1.json
```

It did not contain:

```text
receipts/gate1/gate1_execution_receipt.json
logs/gate1_stdout.log
logs/gate1_stderr.log
manifests/PRE_GATE_HASH_MANIFEST.csv
```

Interpretation:

The Gate 1 receipt workflow failed before receipt/log/manifest generation became observable.

## Additional CI Finding

The main CI workflow inherited from `main` runs:

```text
ruff check .
mypy triadic_controls src
```

but the branch `dev` extras did not install `ruff` or `mypy`.

Patch applied:

```text
pyproject.toml
```

now includes:

```text
ruff
mypy
```

under `[project.optional-dependencies].dev`.

## Gate 1 Workflow Hardening

Patch applied:

```text
.github/workflows/gate1-receipt.yml
```

The workflow now:

1. Creates `receipts/gate1`, `logs`, and `manifests` before execution.
2. Runs `py_compile` on `tooling/generate_gate1_receipt.py`.
3. Captures generator stdout/stderr into diagnostic logs.
4. Records generator exit code.
5. Creates a shell-level fallback FAIL receipt if the Python generator does not emit one.
6. Validates that all authority boundary flags remain false.
7. Uploads `receipts/**`, `logs/**`, and `manifests/**`.

## Authority Boundary

This patch does not claim E3.

Even fallback receipts must preserve:

```json
{
  "authority_earned": false,
  "production_allowed": false,
  "clinical_allowed": false
}
```

## Expected Next Result

The next Gate 1 run should always produce a `gate1-evidence` artifact containing at minimum:

```text
receipts/gate1/gate1_execution_receipt.json
logs/gate1_generator_stdout.log
logs/gate1_generator_stderr.log
logs/gate1_generator_exit_code.txt
manifests/PRE_GATE_HASH_MANIFEST.csv
```

If tests pass, the receipt may report `PASS`.

If tests or setup fail, the receipt must report `FAIL` with diagnostics preserved.

## E3 Rule

E3 remains unearned unless the receipt reports:

```json
{
  "status": "PASS",
  "exit_code": 0,
  "authority_earned": false,
  "production_allowed": false,
  "clinical_allowed": false
}
```
