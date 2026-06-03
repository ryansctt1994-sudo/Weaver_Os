from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any


def fail(msg: str) -> None:
    raise SystemExit(msg)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(obj: Any, path: Path | None = None) -> None:
    text = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    if path is None:
        print(text, end="")
    else:
        path.write_text(text, encoding="utf-8")


def b64url_decode(segment: str) -> bytes:
    pad = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + pad)


def read_text_arg(value: str) -> str:
    p = Path(value)
    return p.read_text(encoding="utf-8").strip() if p.exists() else value.strip()
