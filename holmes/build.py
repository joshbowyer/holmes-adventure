"""Compile story sources into the encoded case files that ship with the game.

  python -m holmes.build

Reads every folder in spoilers/stories/ (all *.toml files in a folder are merged, so
a big case can be split into rooms.toml, people.toml, ...), validates it, drops the
private [test] section, and writes holmes/data/<id>.case. Needs Python 3.11+ (tomllib);
the game itself does not.

Output names ids and counts only, never story text.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from holmes.engine import codec
from holmes.validate import validate

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "spoilers" / "stories"
DATA_DIR = Path(__file__).resolve().parent / "data"


def merge(a: dict, b: dict, path: str = "") -> dict:
    for k, v in b.items():
        if k not in a:
            a[k] = v
        elif isinstance(a[k], dict) and isinstance(v, dict):
            merge(a[k], v, f"{path}{k}.")
        elif isinstance(a[k], list) and isinstance(v, list):
            a[k] = a[k] + v
        else:
            raise ValueError(f"{path}{k} is defined in more than one file")
    return a


def load_source(case_dir: Path) -> dict:
    data: dict = {}
    for p in sorted(case_dir.glob("*.toml")):
        with p.open("rb") as f:
            merge(data, tomllib.load(f))
    return data


def source_dirs() -> list[Path]:
    if not SRC_DIR.exists():
        return []
    return [d for d in sorted(SRC_DIR.iterdir()) if d.is_dir() and any(d.glob("*.toml"))]


def build() -> int:
    DATA_DIR.mkdir(exist_ok=True)
    failed = 0
    for d in source_dirs():
        data = load_source(d)
        errs = validate(data)
        cid = data.get("case", {}).get("id", d.name)
        if errs:
            failed += 1
            print(f"FAILED {cid}:")
            for e in errs:
                print(f"  - {e}")
            continue
        shipped = {k: v for k, v in data.items() if k != "test"}
        (DATA_DIR / f"{cid}.case").write_text(codec.encode(shipped), encoding="utf-8", newline="\n")
        print(f"built {cid}: {len(data.get('rooms', {}))} rooms, {len(data.get('items', {}))} items, "
              f"{len(data.get('characters', {}))} people, {len(data.get('clues', {}))} clues")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(build())
