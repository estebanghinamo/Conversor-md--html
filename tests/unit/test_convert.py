import pytest

import markforge
from markforge import LexerError, MarkdownError, ParserError, convert
from markforge.lexer import MAX_INPUT_LENGTH


def test_convert_is_public() -> None:
    assert "convert" in markforge.__all__


def test_convert_basic_document() -> None:
    assert convert("# Hola\n\n- a\n- b\n") == "<h1>Hola</h1>\n<ul>\n<li>a</li>\n<li>b</li>\n</ul>\n"


def test_convert_empty_input() -> None:
    assert convert("") == ""


def test_convert_neutralizes_html_and_dangerous_urls() -> None:
    result = convert("<script>alert(1)</script> [x](javascript:alert) ![i](data:x)")
    assert "<script" not in result
    assert "href" not in result
    assert "<img" not in result


def test_convert_keeps_safe_links() -> None:
    result = convert("[x](https://a.b)")
    assert result == '<p><a href="https://a.b" rel="noopener noreferrer">x</a></p>\n'


def test_convert_raises_lexer_error_over_limit() -> None:
    with pytest.raises(LexerError):
        convert("a" * (MAX_INPUT_LENGTH + 1))


def test_convert_raises_parser_error_on_deep_nesting() -> None:
    with pytest.raises(ParserError):
        convert(">" * 50 + " x")


def test_all_convert_errors_are_markdown_errors() -> None:
    with pytest.raises(MarkdownError):
        convert(">" * 50 + " x")


def test_convert_normalizes_crlf() -> None:
    assert convert("a\r\nb\r\n\r\n# T\r\n") == "<p>a\nb</p>\n<h1>T</h1>\n"


def test_convert_escapes_html_in_text() -> None:
    assert convert("a < b & c") == "<p>a &lt; b &amp; c</p>\n"


def test_convert_accepts_exact_limit_on_short_lines() -> None:
    line = "a" * 99 + "\n"
    text = (line * (MAX_INPUT_LENGTH // len(line) + 1))[:MAX_INPUT_LENGTH]
    assert convert(text).startswith("<p>")


def test_convert_fence_with_control_character_in_info_string() -> None:
    result = convert("```" + chr(31) + "\ncode\n```")
    assert result == "<pre><code>code\n</code></pre>\n"
