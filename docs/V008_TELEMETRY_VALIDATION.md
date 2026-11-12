# V008 telemetry validation follow-up

This follow-up is based on PR #132 source
`8f8a12a8e1008b46de3368aa9587a7aabebcce6d`.

A private telemetry file with valid JSON but a non-object `counters` value used to
raise `AttributeError` during startup. The loader now validates that container
before iterating it, routing malformed telemetry through the existing corruption
recovery path. The original bytes are set aside, counts restart, and subsequent
events can be persisted normally. Five regression cases cover arrays, null,
strings, booleans and numbers; all five failed before the fix.

The trusted-path loose-mode test now explicitly sets its fixture directory to
0755. `mkdir(mode=0755)` alone creates 0700 under umask 0077, so the previous test
mistook a secure directory for its intended insecure fixture. This test also
failed before the change under umask 0077.

Validation uses `python -m tools.verify_all`, the Python 3.10–3.13 test matrix,
and the root-required isolation and V008 mutation checks. There is no repository
`/validate` command or Makefile target. Raw reports bind results to the tested
commit and are retained separately from the source tree.

These changes do not promote telemetry into execution evidence. V008 HOLD and
E2 / W0 / O0 remain unchanged.
