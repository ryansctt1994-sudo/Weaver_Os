"""Download the pinned TLC JAR and fail closed on a digest mismatch."""

from __future__ import annotations

import argparse
import hashlib
import urllib.request
from pathlib import Path

TLC_URL = "https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar"
TLC_SHA256 = "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    args.destination.parent.mkdir(parents=True, exist_ok=True)

    with urllib.request.urlopen(TLC_URL, timeout=120) as response:
        data = response.read()

    actual = hashlib.sha256(data).hexdigest()
    if actual != TLC_SHA256:
        raise SystemExit(f"TLC digest mismatch: expected {TLC_SHA256}, got {actual}")

    args.destination.write_bytes(data)
    print(f"TLC 1.7.4 verified sha256={actual}")


if __name__ == "__main__":
    main()
