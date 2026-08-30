#!/usr/bin/env python3
"""Incrementa a versão patch em VERSION (ex: 1.2.0 -> 1.2.1). Uso: python scripts/bump_version.py [major|minor|patch]"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
VF = ROOT / "VERSION"

def bump(kind: str = "patch") -> str:
    cur = VF.read_text(encoding="utf-8").strip() if VF.exists() else "0.0.0"
    try:
        major, minor, patch = map(int, cur.split("."))
    except Exception:
        major, minor, patch = 0, 0, 0
    if kind == "major":
        major += 1
        minor = 0
        patch = 0
    elif kind == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1
    nxt = f"{major}.{minor}.{patch}"
    VF.write_text(nxt + "\n", encoding="utf-8")
    print(nxt)
    return nxt

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        raise SystemExit(0)
    kind = sys.argv[1] if len(sys.argv) > 1 else "patch"
    if kind not in ("major", "minor", "patch"):
        print(f"tipo inválido: {kind} (use major|minor|patch)", file=sys.stderr)
        raise SystemExit(1)
    bump(kind)
