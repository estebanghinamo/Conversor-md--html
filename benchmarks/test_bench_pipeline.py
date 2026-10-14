"""Benchmarks del pipeline (pytest-benchmark). Se lanzan a mano: ver docs/testing.md.

Los inputs se generan aqui y quedan por debajo de los limites del lexer y el parser, para medir
trabajo real y no el camino de error. No hay umbrales de tiempo: son numeros de referencia.
"""

from collections.abc import Callable

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from markforge import convert
from markforge.ast import Document
from markforge.lexer import MAX_INPUT_LENGTH, Token, tokenize
from markforge.parser import parse
from markforge.renderer import render
from markforge.sanitizer import sanitize

_TYPICAL_BLOCK = (
    "# Titulo de seccion\n\n"
    "Un parrafo con **negrita**, *enfasis*, `codigo`, ~~tachado~~ y un "
    "[enlace](https://example.com/ruta) junto a ![imagen](https://example.com/i.png).\n\n"
    "- elemento uno\n- elemento dos\n- elemento tres\n\n"
    "1. primero\n2. segundo\n\n"
    "> una cita con *enfasis*\n\n"
    "```python\nprint('hola')\n```\n\n"
    "| col a | col b | col c |\n|:--|:-:|--:|\n| 1 | 2 | 3 |\n| 4 | 5 | 6 |\n\n"
    "---\n\n"
)


def _typical(repeat: int) -> str:
    return _TYPICAL_BLOCK * repeat


def _near_limit() -> str:
    text = "linea de texto con **negrita** y [enlace](https://example.com)\n\n" * 40_000
    return text[: MAX_INPUT_LENGTH - 100]


def _big_table() -> str:
    columns = 20
    header = "|".join(f"c{i}" for i in range(columns))
    rule = "|".join(["---"] * columns)
    row = "|".join(["valor"] * columns)
    return "\n".join([header, rule, *[row] * 4_000]) + "\n"


def _run_big(benchmark: BenchmarkFixture, func: Callable[[], object]) -> None:
    benchmark.pedantic(func, rounds=3, iterations=1, warmup_rounds=1)  # type: ignore[no-untyped-call]


# --- Etapas sobre un documento tipico (~170 KB) -------------------------------------------------


@pytest.fixture(scope="module")
def typical_source() -> str:
    return _typical(500)


@pytest.fixture(scope="module")
def typical_tokens(typical_source: str) -> list[Token]:
    return tokenize(typical_source)


@pytest.fixture(scope="module")
def typical_document(typical_tokens: list[Token]) -> Document:
    return parse(typical_tokens)


@pytest.fixture(scope="module")
def typical_sanitized(typical_document: Document) -> Document:
    return sanitize(typical_document)


def test_stage_lexer(benchmark: BenchmarkFixture, typical_source: str) -> None:
    benchmark(tokenize, typical_source)


def test_stage_parser(benchmark: BenchmarkFixture, typical_tokens: list[Token]) -> None:
    benchmark(parse, typical_tokens)


def test_stage_sanitizer(benchmark: BenchmarkFixture, typical_document: Document) -> None:
    benchmark(sanitize, typical_document)


def test_stage_renderer(benchmark: BenchmarkFixture, typical_sanitized: Document) -> None:
    benchmark(render, typical_sanitized)


def test_convert_typical(benchmark: BenchmarkFixture, typical_source: str) -> None:
    benchmark(convert, typical_source)


# --- Entradas grandes o dificiles ---------------------------------------------------------------


def test_convert_near_input_limit(benchmark: BenchmarkFixture) -> None:
    source = _near_limit()
    _run_big(benchmark, lambda: convert(source))


def test_convert_big_table(benchmark: BenchmarkFixture) -> None:
    source = _big_table()
    _run_big(benchmark, lambda: convert(source))


def test_convert_long_line(benchmark: BenchmarkFixture) -> None:
    source = "palabra " * 12_000 + "\n"
    benchmark(convert, source)


def test_convert_nested_emphasis(benchmark: BenchmarkFixture) -> None:
    source = ("*a **b " * 400) + ("c** d*" * 400) + "\n"
    benchmark(convert, source)


def test_convert_many_brackets(benchmark: BenchmarkFixture) -> None:
    source = "[a](https://example.com) " * 900 + "[sin cerrar " * 90 + "\n"
    benchmark(convert, source)


def test_convert_many_delimiters(benchmark: BenchmarkFixture) -> None:
    source = "*x " * 1_500 + "\n"
    benchmark(convert, source)
