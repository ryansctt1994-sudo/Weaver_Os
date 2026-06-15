#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/.."

bundle="weaver-audit-package-$(date +%Y%m%d).tar.gz"
tar -czf "$bundle" audit-package

echo "Created $bundle"
