"""Fuzzing del lexer con Atheris (workflow aparte: .github/workflows/fuzz.yml).

Atheris no corre en Windows. En Linux/WSL: `uv run --group fuzz python tests/fuzz/fuzz_lexer.py`.
"""

import contextlib
import sys

from markforge import LexerError
from markforge.lexer import tokenize


def test_one_input(data: bytes) -> None:
    """Valido: tokeniza o lanza `LexerError`; cualquier otra excepcion es un bug."""
    source = data.decode("utf-8", errors="replace")
    with contextlib.suppress(LexerError):
        tokenize(source)


def main() -> None:
    import atheris

    atheris.instrument_all()
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
