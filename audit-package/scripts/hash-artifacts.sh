#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

find . -type f \
  ! -path './.git/*' \
  ! -path './SHA256SUMS.txt' \
  | sort \
  | xargs sha256sum > SHA256SUMS.txt

echo "Wrote SHA256SUMS.txt"
