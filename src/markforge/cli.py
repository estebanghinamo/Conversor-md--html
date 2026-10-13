"""Interfaz de línea de comandos (solo E/S)."""

import argparse
from collections.abc import Sequence

from markforge.version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markforge",
        description="Convierte un subconjunto de Markdown a HTML.",
    )
    parser.add_argument("--version", action="version", version=f"markforge {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    return 0
