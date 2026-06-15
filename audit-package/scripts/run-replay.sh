#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== Weaver Audit Package Replay =="
echo "Mode: diagnostic / reviewer-executable"
echo

./scripts/validate-manifests.sh
./scripts/verify-receipts.sh

echo
echo "Replay package review files:"
echo "- E3_1_RECEIPTED_REPLAY_PACKAGE.md"
echo "- REPRODUCTION_INSTRUCTIONS.md"
echo "- REPLAY_REPORT.md"
echo "- VERIFICATION_REPORT.md"
echo
echo "Replay diagnostic complete. No authority promotion performed."
