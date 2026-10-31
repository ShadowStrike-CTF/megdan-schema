#!/usr/bin/env python3
"""Print the SHA-256 of every vendorable file in megdan_schema, for hosts to pin.

Output is ``sha256sum`` format, with paths relative to the package's parent folder:

    <hex>  megdan_schema/encoding.py

A host that vendors the package into ``vendor/megdan_schema/`` can save this output as
``vendor/megdan_schema.sha256`` and check it with ``cd vendor && sha256sum -c megdan_schema.sha256``.
Stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
from collections.abc import Sequence
from pathlib import Path

DEFAULT_PACKAGE = Path(__file__).resolve().parent.parent / "src" / "megdan_schema"


def vendorable_files(package_dir: Path) -> list[Path]:
    """Every file in the package except bytecode caches, sorted."""
    return sorted(
        p
        for p in package_dir.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}
    )


def file_hashes(package_dir: Path) -> list[tuple[str, str]]:
    """``[(hex, "megdan_schema/x.py"), ...]``."""
    base = package_dir.parent
    return [
        (hashlib.sha256(p.read_bytes()).hexdigest(), p.relative_to(base).as_posix())
        for p in vendorable_files(package_dir)
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print SHA-256 pins for vendoring megdan_schema.")
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE, help="package directory")
    args = parser.parse_args(argv)
    if not args.package.is_dir():
        parser.error(f"not a directory: {args.package}")
    for digest, rel in file_hashes(args.package):
        print(f"{digest}  {rel}")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via main() in tests
    raise SystemExit(main())
