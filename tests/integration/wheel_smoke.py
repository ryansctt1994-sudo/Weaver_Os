"""Execute with isolated Python outside the checkout after wheel installation."""

import json
import sys
from pathlib import Path

from weaver_verifier.public_log import PublicLogProofError, verify_publication

from triadic_controls.ledger import verify_chain

fixture = Path(sys.argv[1])
assert len(verify_chain([json.loads(line) for line in fixture.read_text().splitlines()])) == 3
print("Installed-wheel ledger/schema verification PASS")
try:
    verify_publication(b"", b"[]", b"")
except PublicLogProofError:
    print("Installed-wheel offline proof module/refusal PASS")
else:
    raise AssertionError("malformed publication proof was accepted")
