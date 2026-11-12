"""Read a retained publication proof; no network or effect execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from weaver_verifier.public_log import verify_publication


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("entry", type=Path)
    parser.add_argument("log_key", type=Path)
    args = parser.parse_args()
    values = []
    for path in (args.manifest, args.entry, args.log_key):
        with path.open("rb") as stream:
            values.append(stream.read(1024 * 1024 + 1))
    print(json.dumps(verify_publication(*values), indent=2))


if __name__ == "__main__":
    main()
