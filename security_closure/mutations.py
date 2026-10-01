"""Mutants run in memory; production code has no bypass switches."""

import json
from pathlib import Path

from security_closure.run import CORPUS, run_case

MUTATIONS = {
    "identity_gate": ("principal != request.actor", "False", "stolen_token"),
    "request_binding": ("approval[0] != request.digest()", "False", "request_substitution"),
    "approval_replay": ("now >= approval[1] or approval[2]", "False", "restart_replay"),
    "lineage_gate": ("not self.lineage_valid(db, grant, request, now)", "False", "forged_grant"),
    "ancestor_revocation": (
        "if revoked or now >= expires",
        "if False or now >= expires",
        "revoked_parent",
    ),
    "action_gate": ("request.action != \"increment\"", "False", "scope_escalation"),
    "atomic_effect": (
        "if crash == \"before_commit\":",
        "if crash == \"before_commit\":\n                    db.commit()",
        "crash_before_commit",
    ),
}


def main():
    source = Path(__file__).with_name("boundary.py").read_text()
    cases = {c["id"]: c for c in json.loads(CORPUS.read_text())}
    outcomes = {}
    for name, (old, new, attack) in MUTATIONS.items():
        assert source.count(old) == 1, name
        namespace = {"__name__": "security_closure.mutant"}
        exec(compile(source.replace(old, new), f"<{name}>", "exec"), namespace)
        try:
            run_case(cases[attack], namespace["Boundary"])
        except AssertionError:
            outcomes[name] = "KILLED"
        else:
            outcomes[name] = "SURVIVED"
    print(json.dumps(outcomes, indent=2))
    if any(value != "KILLED" for value in outcomes.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
