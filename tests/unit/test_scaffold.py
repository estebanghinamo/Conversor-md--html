import pytest

from markforge import MarkdownError, __version__
from markforge.cli import main
from markforge.errors import LexerError, ParserError, RenderError, SanitizationError


def test_version_is_defined() -> None:
    assert __version__


@pytest.mark.parametrize("error", [LexerError, ParserError, SanitizationError, RenderError])
def test_errors_inherit_from_markdown_error(error: type[MarkdownError]) -> None:
    assert issubclass(error, MarkdownError)


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert f"markforge {__version__}" in capsys.readouterr().out


def test_cli_without_args_returns_zero() -> None:
    assert main([]) == 0
