"""Prueba de humo del harness de fuzzing (sin Atheris): el lexer solo puede lanzar `LexerError`."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from markforge import LexerError
from markforge.lexer import MAX_INPUT_LENGTH, tokenize

_HARNESS = Path(__file__).resolve().parents[1] / "fuzz" / "fuzz_lexer.py"


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("fuzz_lexer", _HARNESS)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"# titulo\n\n- a\n- b\n",
        b"| a | b |\n|:-:|--:|\n| 1 | 2 |\n",
        b"```py\ncodigo",
        b"<div>\n</div>\n",
        b"\xff\xfe\x00\x80",
        b"|" * 500 + b"\n" + b"|-" * 500,
    ],
)
def test_harness_accepts_inputs(data: bytes) -> None:
    _load_harness().test_one_input(data)


def test_harness_accepts_lexer_error() -> None:
    data = b"a" * (MAX_INPUT_LENGTH + 1)
    with pytest.raises(LexerError):
        tokenize(data.decode())
    _load_harness().test_one_input(data)


def test_harness_propagates_other_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_source: str) -> None:
        msg = "bug"
        raise ValueError(msg)

    harness = _load_harness()
    monkeypatch.setattr(harness, "tokenize", boom)
    with pytest.raises(ValueError, match="bug"):
        harness.test_one_input(b"x")
