import pytest

from markforge.errors import LexerError
from markforge.lexer import MAX_INPUT_LENGTH, MAX_LINE_LENGTH, MAX_LINES, Token, TokenType, tokenize

NEWLINE = chr(10)


def one(source: str) -> Token:
    tokens = tokenize(source)
    assert len(tokens) == 1
    return tokens[0]


def test_empty_input_has_no_tokens() -> None:
    assert tokenize("") == []


def test_trailing_newline_adds_no_blank_token() -> None:
    assert [t.type for t in tokenize("a\n")] == [TokenType.TEXT]
    assert [t.type for t in tokenize("a\n\n")] == [TokenType.TEXT, TokenType.BLANK]


@pytest.mark.parametrize("source", ["a\r\nb", "a\rb", "a\nb"])
def test_line_endings_are_normalized(source: str) -> None:
    assert [(t.value, t.line) for t in tokenize(source)] == [("a", 1), ("b", 2)]


def test_blank_line_with_whitespace() -> None:
    assert one("  \t ").type is TokenType.BLANK


@pytest.mark.parametrize("level", range(1, 7))
def test_heading_levels(level: int) -> None:
    token = one("#" * level + " Título")
    assert (token.type, token.level, token.value) == (TokenType.HEADING, level, "Título")


@pytest.mark.parametrize(
    ("source", "value"),
    [("# Hola #", "Hola"), ("# Hola ###", "Hola"), ("# C#", "C#"), ("# ###", ""), ("#", "")],
)
def test_heading_closing_hashes(source: str, value: str) -> None:
    token = one(source)
    assert (token.type, token.value) == (TokenType.HEADING, value)


@pytest.mark.parametrize("source", ["####### siete", "#sinespacio"])
def test_not_a_heading(source: str) -> None:
    assert one(source).type is TokenType.TEXT


@pytest.mark.parametrize("source", ["---", "***", "___", "- - -", "* * *", "-----", " ***"])
def test_horizontal_rule(source: str) -> None:
    assert one(source).type is TokenType.HORIZONTAL_RULE


@pytest.mark.parametrize("source", ["--", "-*-", "- -"])
def test_not_a_horizontal_rule(source: str) -> None:
    assert one(source).type is not TokenType.HORIZONTAL_RULE


@pytest.mark.parametrize(
    ("source", "value"), [("> cita", "cita"), (">cita", "cita"), ("> > x", "> x")]
)
def test_blockquote(source: str, value: str) -> None:
    token = one(source)
    assert (token.type, token.value) == (TokenType.BLOCKQUOTE, value)


@pytest.mark.parametrize("marker", ["-", "*", "+"])
def test_unordered_list_item(marker: str) -> None:
    token = one(f"{marker} item")
    assert (token.type, token.ordered, token.value) == (TokenType.LIST_ITEM, False, "item")


@pytest.mark.parametrize("source", ["1. uno", "42. uno", "123456789. uno"])
def test_ordered_list_item(source: str) -> None:
    token = one(source)
    assert (token.type, token.ordered, token.value) == (TokenType.LIST_ITEM, True, "uno")


@pytest.mark.parametrize(
    "source", ["-item", "1.uno", "1000000000. uno", ". x", "1) x", "-a", "1.a"]
)
def test_not_a_list_item(source: str) -> None:
    assert one(source).type is TokenType.TEXT


def test_inline_markup_is_left_untouched() -> None:
    token = one("**negrita** y `code` [a](http://x)")
    assert token.value == "**negrita** y `code` [a](http://x)"


def test_html_is_not_interpreted() -> None:
    assert one("<script>alert(1)</script>").value == "<script>alert(1)</script>"


def test_four_space_indent_is_plain_text() -> None:
    assert one("    # no heading").type is TokenType.TEXT
    assert one("\t- no item").type is TokenType.TEXT


def test_up_to_three_spaces_of_indent_are_allowed() -> None:
    assert one("   # titulo").type is TokenType.HEADING


def test_code_block_with_language() -> None:
    token = one("```python\nprint(1)\n\n# no heading\n```")
    assert token.type is TokenType.CODE_BLOCK
    assert token.language == "python"
    assert token.value == "print(1)\n\n# no heading"


def test_code_block_without_language_and_empty() -> None:
    token = one("```\n```")
    assert (token.language, token.value) == (None, "")


def test_unclosed_code_block_runs_to_end() -> None:
    tokens = tokenize("```\na\nb")
    assert [(t.type, t.value) for t in tokens] == [(TokenType.CODE_BLOCK, "a\nb")]


def test_longer_fence_closes_only_with_enough_backticks() -> None:
    token = one("````\n```\nx\n````")
    assert token.value == "```\nx"


def test_code_block_followed_by_more_tokens() -> None:
    tokens = tokenize("```\nx\n```\n# fin")
    assert [(t.type, t.line) for t in tokens] == [(TokenType.CODE_BLOCK, 1), (TokenType.HEADING, 4)]


def test_fence_with_backtick_in_info_is_text() -> None:
    assert one("```a`b").type is TokenType.TEXT


def test_indented_four_spaces_is_not_a_fence() -> None:
    assert one("    ```").type is TokenType.TEXT


def test_closing_fence_indented_four_spaces_does_not_close() -> None:
    token = one("```\nx\n    ```")
    assert token.value == "x\n    ```"


def test_fence_language_is_first_word_of_info_string() -> None:
    assert one("```python title=x\n```").language == "python"


def test_closing_fence_may_be_longer_than_opening() -> None:
    tokens = tokenize("```\nx\n`````\n# fin")
    assert [(t.type, t.value) for t in tokens] == [
        (TokenType.CODE_BLOCK, "x"),
        (TokenType.HEADING, "fin"),
    ]


def test_closing_fence_with_trailing_text_does_not_close() -> None:
    assert one("```\nx\n``` y").value == "x\n``` y"


def test_lone_newline_is_a_single_blank() -> None:
    assert [t.type for t in tokenize("\n")] == [TokenType.BLANK]


def test_heading_with_tab_separator() -> None:
    token = one("#\tTítulo")
    assert (token.type, token.level, token.value) == (TokenType.HEADING, 1, "Título")


def test_tabs_inside_rule_are_ignored() -> None:
    assert one("-\t-\t-").type is TokenType.HORIZONTAL_RULE


def test_list_item_with_tab_after_marker() -> None:
    token = one("-\titem")
    assert (token.type, token.value) == (TokenType.LIST_ITEM, "item")


def test_line_numbers_are_one_based() -> None:
    assert [t.line for t in tokenize("# a\n\ntexto\n- x")] == [1, 2, 3, 4]


def test_mixed_document() -> None:
    tokens = tokenize("# T\n\npárrafo\n\n- a\n- b\n\n> q\n\n---\n")
    assert [t.type for t in tokens] == [
        TokenType.HEADING,
        TokenType.BLANK,
        TokenType.TEXT,
        TokenType.BLANK,
        TokenType.LIST_ITEM,
        TokenType.LIST_ITEM,
        TokenType.BLANK,
        TokenType.BLOCKQUOTE,
        TokenType.BLANK,
        TokenType.HORIZONTAL_RULE,
    ]


def test_input_too_large_raises() -> None:
    with pytest.raises(LexerError, match="input excede"):
        tokenize("a" * (MAX_INPUT_LENGTH + 1))


def test_line_too_long_raises() -> None:
    with pytest.raises(LexerError, match="línea 2 excede"):
        tokenize("ok\n" + "a" * (MAX_LINE_LENGTH + 1))


def test_line_at_limit_is_accepted() -> None:
    assert one("a" * MAX_LINE_LENGTH).type is TokenType.TEXT


def test_pathological_input_is_linear() -> None:
    assert tokenize("#" * 50_000 + "\n" + "- " * 20_000 + "\n" + "`" * 50_000)


@pytest.mark.parametrize(("source", "ordered"), [("-", False), ("*", False), ("1.", True)])
def test_empty_list_item(source: str, ordered: bool) -> None:
    token = one(source)
    assert (token.type, token.ordered, token.value) == (TokenType.LIST_ITEM, ordered, "")


def test_too_many_lines_raises() -> None:
    with pytest.raises(LexerError, match="líneas"):
        tokenize(NEWLINE * (MAX_LINES + 1))


def test_lines_at_limit_are_accepted() -> None:
    assert len(tokenize(NEWLINE * MAX_LINES)) == MAX_LINES


def test_only_space_and_tab_count_as_whitespace() -> None:
    nbsp = chr(0xA0)
    assert one(nbsp).type is TokenType.TEXT
    assert one("#" + nbsp + "x").type is TokenType.TEXT


@pytest.mark.parametrize("code", [0x1C, 0x1F, 0x85, 0xA0, 0x2028])
def test_fence_info_made_of_unicode_whitespace_does_not_crash(code: int) -> None:
    char = chr(code)
    token = one("```" + char + "\nx\n```")
    assert (token.type, token.value) == (TokenType.CODE_BLOCK, "x")
    assert token.language == char


def test_fence_language_is_the_first_word_split_by_space_or_tab() -> None:
    assert one("```py" + chr(9) + "title\nx\n```").language == "py"
    assert one("```py  title\nx\n```").language == "py"
