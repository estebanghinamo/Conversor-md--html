import pytest

from markforge import MarkdownError, __version__
from markforge.errors import LexerError, ParserError, RenderError, SanitizationError


def test_version_is_defined() -> None:
    assert __version__


@pytest.mark.parametrize("error", [LexerError, ParserError, SanitizationError, RenderError])
def test_errors_inherit_from_markdown_error(error: type[MarkdownError]) -> None:
    assert issubclass(error, MarkdownError)
