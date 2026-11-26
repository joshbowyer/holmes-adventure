"""Light obfuscation for shipped story data and save files.

This is not security. It only stops a stray `cat` or `grep` from spoiling a case:
JSON -> zlib -> XOR with a fixed key -> base85, wrapped at 76 columns.
"""

from __future__ import annotations

import base64
import json
import zlib

HEADER = "HOLMES1"
_KEY = b"221B Baker Street, London, N.W."


def _xor(data: bytes) -> bytes:
    key = _KEY
    n = len(key)
    return bytes(b ^ key[i % n] for i, b in enumerate(data))


def encode(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    body = base64.b85encode(_xor(zlib.compress(raw, 9))).decode("ascii")
    lines = [body[i:i + 76] for i in range(0, len(body), 76)]
    return HEADER + "\n" + "\n".join(lines) + "\n"


def decode(text: str):
    head, _, body = text.partition("\n")
    if head.strip() != HEADER:
        raise ValueError("not a Holmes data file")
    packed = base64.b85decode("".join(body.split()))
    return json.loads(zlib.decompress(_xor(packed)).decode("utf-8"))
