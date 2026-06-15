#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

required=(
  "README.md"
  "PACKAGE_INDEX.md"
  "AUDIT_PACKAGE.md"
  "CLAIMS_AND_EVIDENCE.md"
  "VERIFY.md"
  "E3_1_RECEIPTED_REPLAY_PACKAGE.md"
  "REPRODUCTION_INSTRUCTIONS.md"
  "REPLAY_REPORT.md"
  "VERIFICATION_REPORT.md"
  "EVIDENCE_MANIFEST.md"
  "CHAIN_INTEGRITY_REPORT.md"
  "CLAIM_TRACEABILITY_MATRIX.md"
  "WITNESS_ATTESTATIONS.md"
  "FAILURE_AND_COUNTEREXAMPLE_LOG.md"
  "LIMITATIONS_AND_NONCLAIMS.md"
  "REVIEWER_CHECKLIST.md"
  "REVIEWER_CONCLUSION_TEMPLATE.md"
  "ENVIRONMENT_MANIFEST.md"
)

missing=0
for file in "${required[@]}"; do
  if [ ! -f "$file" ]; then
    echo "Missing: $file"
    missing=1
  fi
done

if [ "$missing" -ne 0 ]; then
  echo "Manifest validation failed."
  exit 1
fi

echo "Manifest validation passed."
