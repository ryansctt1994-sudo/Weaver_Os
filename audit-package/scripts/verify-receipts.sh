#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f artifacts/receipts/receipt-index.json ]; then
  echo "No receipt index found: artifacts/receipts/receipt-index.json"
  echo "Receipt verification is pending until real receipts are added."
  exit 0
fi

python3 - <<'PY'
import json
from pathlib import Path

index = Path('artifacts/receipts/receipt-index.json')
data = json.loads(index.read_text())
receipts = data.get('receipts', [])
missing = []
for receipt in receipts:
    path = Path(receipt.get('path', ''))
    if not path.exists():
        missing.append(str(path))

if missing:
    print('Missing receipts:')
    for item in missing:
        print(f'- {item}')
    raise SystemExit(1)

print(f'Verified receipt index entries: {len(receipts)}')
PY
