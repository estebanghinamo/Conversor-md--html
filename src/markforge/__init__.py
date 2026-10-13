"""MarkForge: Markdown a HTML seguro."""

from markforge.errors import (
    LexerError,
    MarkdownError,
    ParserError,
    RenderError,
    SanitizationError,
)
from markforge.lexer import tokenize
from markforge.parser import parse
from markforge.renderer import render
from markforge.sanitizer import sanitize
from markforge.version import __version__


def convert(markdown: str) -> str:
    """Convierte Markdown a un fragmento HTML seguro.

    Recorre el pipeline completo (lexer, parser, sanitizer, renderer). Lanza una
    subclase de `MarkdownError` si el input excede los límites o no es válido.
    """
    return render(sanitize(parse(tokenize(markdown))))


__all__ = [
    "LexerError",
    "MarkdownError",
    "ParserError",
    "RenderError",
    "SanitizationError",
    "__version__",
    "convert",
]
