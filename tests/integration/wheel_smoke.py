"""Execute with isolated Python outside the checkout after wheel installation."""

import json
import sys
from pathlib import Path

from triadic_controls.ledger import verify_chain

fixture = Path(sys.argv[1])
assert len(verify_chain([json.loads(line) for line in fixture.read_text().splitlines()])) == 3
print("Installed-wheel ledger/schema verification PASS")
