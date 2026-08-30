"""JornalDiário — pacote core."""
import pathlib

try:
    _v = (pathlib.Path(__file__).parent.parent / "VERSION").read_text(encoding="utf-8").strip()
except Exception:
    _v = "0.0.0"

__version__ = _v
