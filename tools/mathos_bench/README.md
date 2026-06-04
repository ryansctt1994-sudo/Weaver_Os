# MATHOS BENCH v0.1

Status: experimental verification harness. Not canonical. Not authority.

MATHOS BENCH is a candidate evidence-inflation and error-catch harness for evaluating MATHOS PRIME v2.1. It is included in Weaver OS as an experimental tool because it can generate receipts and warnings, but it cannot authorize protocol promotion by itself.

## Boundary

The governing invariant is:

```text
SELF_VERIFICATION_IS_NOT_AUTHORITY
```

A model may propose, critique, organize, and stress-test claims. Promotion to formal, empirical, computational, engineering, or consequential authority requires a verifier that can return no and differs in kind from any model in the loop.

A second language model may critique, but it cannot authorize.

## Bench rule

```text
THE_BENCH_MUST_NOT_LAUNDER_THE_PROTOCOL
```

A benchmark designed, run, and scored within the same model-modality may produce warnings, comparisons, and candidate receipts, but it cannot authorize protocol promotion without an independent key, a non-model scorer where possible, and human or external verifier anchors.

## Files

```text
mathos_bench_v0_1.py                 # deterministic scoring harness and promotion gate
mathos_bench_claimset_key_v0_1.json  # frozen candidate claim set and expected traps
mathos_bench_smoke_receipt_v0_1.json # smoke-test receipt showing VERDICT_WITHHELD
```

## Run

```bash
python tools/mathos_bench/mathos_bench_v0_1.py \
  --claimset tools/mathos_bench/mathos_bench_claimset_key_v0_1.json \
  --runs tools/mathos_bench/mathos_bench_smoke_input_v0_1.json \
  --out /tmp/mathos_bench_receipt.json
```

The included receipt records the smoke-test output directly; a separate `smoke_input` file can be added if the repository should preserve executable replay inputs.

## Expected smoke-test gate

```text
VERDICT_WITHHELD
```

Reason:

```text
scorer is model-modality
key not certified independent
0 human anchors
```

Numeric improvement can warn, but it cannot authorize promotion.
