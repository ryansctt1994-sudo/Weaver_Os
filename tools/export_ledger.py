"""Export a ReceiptLedger's snapshot and anchor as WX-CJSON-1 files.

    python -m tools.export_ledger --db ledger.db --ledger-id wx-main \\
        --snapshot-out snapshot.json --anchor-out anchor.json

The files feed ``python -m weaver_verifier.state`` in a separate process. Producing an
anchor here does not give it external custody. Whoever holds the database can produce
both files. Publish the anchor somewhere the ledger's operator cannot rewrite.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from weaver_contracts.canonical import canonicalize
from weaver_runtime.ledger import ReceiptLedger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--ledger-id", required=True)
    parser.add_argument("--snapshot-out", type=Path, required=True)
    parser.add_argument("--anchor-out", type=Path)
    args = parser.parse_args(argv)
    if not args.db.is_file():
        print(f"FAIL: no ledger store at {args.db}", file=sys.stderr)
        return 1
    with ReceiptLedger(args.db, ledger_id=args.ledger_id) as ledger:
        args.snapshot_out.write_bytes(canonicalize(ledger.snapshot()))
        if args.anchor_out:
            args.anchor_out.write_bytes(canonicalize(ledger.anchor().to_dict()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
