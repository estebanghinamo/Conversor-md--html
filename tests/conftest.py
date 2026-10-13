from collections.abc import Callable

import pytest

from markforge.lexer import tokenize
from markforge.parser import parse
from markforge.renderer import render
from markforge.sanitizer import sanitize


def convert_markdown(source: str) -> str:
    """Compone el pipeline completo: tokenize -> parse -> sanitize -> render."""
    return render(sanitize(parse(tokenize(source))))


@pytest.fixture
def convert() -> Callable[[str], str]:
    return convert_markdown
