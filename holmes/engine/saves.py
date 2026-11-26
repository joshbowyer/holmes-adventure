"""Save files (one per case) and the player profile (settings + case records).

Location: $HOLMES_SAVE_DIR, else $XDG_DATA_HOME/holmes-adventure, else
~/.local/share/holmes-adventure (%APPDATA%\\holmes-adventure on Windows).
Both files use the same light obfuscation as story data.
"""

from __future__ import annotations

import os
from pathlib import Path

from holmes.engine import codec


def save_dir() -> Path:
    env = os.environ.get("HOLMES_SAVE_DIR")
    if env:
        d = Path(env)
    elif os.name == "nt" and os.environ.get("APPDATA"):
        d = Path(os.environ["APPDATA"]) / "holmes-adventure"
    else:
        base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
        d = Path(base) / "holmes-adventure"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read(path: Path):
    try:
        return codec.decode(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(codec.encode(obj), encoding="utf-8")
    os.replace(tmp, path)


def save_path(case_id: str) -> Path:
    return save_dir() / f"{case_id}.sav"


def load_game(case_id: str) -> dict | None:
    return _read(save_path(case_id))


def save_game(state_dict: dict) -> None:
    _write(save_path(state_dict["case_id"]), state_dict)


def delete_game(case_id: str) -> None:
    try:
        save_path(case_id).unlink()
    except FileNotFoundError:
        pass


def load_profile() -> dict:
    p = _read(save_dir() / "profile.dat")
    if not isinstance(p, dict):
        p = {}
    p.setdefault("color", None)
    p.setdefault("cases", {})
    return p


def save_profile(profile: dict) -> None:
    _write(save_dir() / "profile.dat", profile)
