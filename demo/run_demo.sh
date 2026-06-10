#!/usr/bin/env bash
# Cathedral-OS Boundary Integrity Demo Core Execution Harness
# Status: CANONICAL_DEMO_RUNNER

set -euo pipefail

printf "\n[THE THRONE REMAINS EMPTY: VALIDATION ALGEBRA INTEGRITY HARNESS]\n"

python3 demo/boundary_integrity_demo.py demo/demo_cases/01_valid_ordinary_proposal.json
python3 demo/boundary_integrity_demo.py demo/demo_cases/02_authority_leak_attempt.json
python3 demo/boundary_integrity_demo.py demo/demo_cases/03_tampered_record.json
python3 demo/boundary_integrity_demo.py demo/demo_cases/04_cvp_promotion_without_witness.json

printf "[SUITE COMPLETE: EXPLOIT SMUGGLING BLOCKED CONTINUOUSLY]\n\n"
