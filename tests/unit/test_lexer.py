import contextlib

import pytest

from markforge.errors import LexerError
from markforge.lexer import (
    MAX_INPUT_LENGTH,
    MAX_LINE_LENGTH,
    MAX_LINES,
    MAX_TABLE_CELLS,
    MAX_TABLE_COLUMNS,
    Token,
    TokenType,
    tokenize,
)

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


# --- tablas ----------------------------------------------------------------------------------


def table(source: str) -> Token:
    token = one(source)
    assert token.type is TokenType.TABLE
    return token


def kinds(source: str) -> list[TokenType]:
    return [token.type for token in tokenize(source)]


def test_basic_table() -> None:
    token = table("| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |")
    assert token.rows == (("a", "b"), ("1", "2"), ("3", "4"))
    assert token.aligns == (None, None)
    assert token.line == 1


def test_table_without_outer_pipes() -> None:
    assert table("a | b\n--|--\n1 | 2").rows == (("a", "b"), ("1", "2"))


def test_table_with_only_a_header_has_no_body_rows() -> None:
    assert table("a|b\n-|-\n").rows == (("a", "b"),)


def test_table_alignments() -> None:
    token = table("a|b|c|d\n:--|:-:|--:|---")
    assert token.aligns == ("left", "center", "right", None)


def test_alignment_marker_needs_at_least_one_dash() -> None:
    assert kinds("a|b\n:|-") == [TokenType.TEXT, TokenType.TEXT]
    assert kinds("a|b\n::|--") == [TokenType.TEXT, TokenType.TEXT]
    assert kinds("a|b\n|-") == [TokenType.TEXT, TokenType.TEXT]


def test_escaped_pipe_is_a_literal_pipe_in_the_cell() -> None:
    token = table("a|b\n-|-\nx" + chr(92) + "|y|z")
    assert token.rows[1] == ("x|y", "z")


def test_pipe_at_the_end_of_a_row_does_not_add_a_cell() -> None:
    assert table("a|b|\n-|-|\n1|2|").rows == (("a", "b"), ("1", "2"))


def test_short_rows_are_padded_and_long_rows_truncated() -> None:
    token = table("a|b|c\n-|-|-\n1|x\n1|2|3|4|5")
    assert token.rows[1:] == (("1", "x", ""), ("1", "2", "3"))


def test_row_that_is_only_a_pipe_gives_empty_cells() -> None:
    assert table("a|b\n-|-\n|").rows[1] == ("", "")


def test_table_inline_markup_is_left_raw() -> None:
    assert table("**a**|`b`\n-|-").rows == (("**a**", "`b`"),)


def test_header_without_an_alignment_row_is_not_a_table() -> None:
    assert kinds("a|b\nc|d") == [TokenType.TEXT, TokenType.TEXT]
    assert kinds("a|b") == [TokenType.TEXT]


def test_header_without_pipe_is_not_a_table() -> None:
    assert kinds("ab\n-|-") == [TokenType.TEXT, TokenType.TEXT]


def test_alignment_row_without_pipe_is_not_a_table() -> None:
    assert kinds("a|b\n---") == [TokenType.TEXT, TokenType.HORIZONTAL_RULE]


def test_alignment_row_with_other_characters_is_not_a_table() -> None:
    assert kinds("a|b\n-x|--") == [TokenType.TEXT, TokenType.TEXT]


def test_alignment_row_indented_four_spaces_is_not_a_table() -> None:
    assert kinds("a|b\n    -|-") == [TokenType.TEXT, TokenType.TEXT]


def test_header_and_alignment_row_with_different_column_counts_are_not_a_table() -> None:
    assert kinds("a|b|c\n--|--") == [TokenType.TEXT, TokenType.TEXT]
    assert kinds("a|b\n--|--|--") == [TokenType.TEXT, TokenType.TEXT]


@pytest.mark.parametrize("header", ["# a|b", "> a|b", "- a|b", "```a|b"])
def test_header_must_be_a_plain_text_line(header: str) -> None:
    assert TokenType.TABLE not in kinds(header + "\n-|-")


def test_table_ends_at_a_blank_line() -> None:
    tokens = tokenize("a|b\n-|-\n1|2\n\n3|4")
    assert [t.type for t in tokens] == [TokenType.TABLE, TokenType.BLANK, TokenType.TEXT]
    assert tokens[0].rows == (("a", "b"), ("1", "2"))


@pytest.mark.parametrize(
    ("after", "kind"),
    [
        ("# h", TokenType.HEADING),
        ("---", TokenType.HORIZONTAL_RULE),
        ("> q", TokenType.BLOCKQUOTE),
        ("- i", TokenType.LIST_ITEM),
    ],
)
def test_table_ends_at_another_block(after: str, kind: TokenType) -> None:
    tokens = tokenize("a|b\n-|-\n1|2\n" + after)
    assert [t.type for t in tokens] == [TokenType.TABLE, kind]
    assert tokens[1].line == 4


def test_table_ends_at_a_code_fence_and_the_fence_is_still_read() -> None:
    tokens = tokenize("a|b\n-|-\n```\nx|y\n```")
    assert [t.type for t in tokens] == [TokenType.TABLE, TokenType.CODE_BLOCK]
    assert tokens[1].value == "x|y"


def test_table_ends_at_a_line_made_only_of_html_tags() -> None:
    assert kinds("a|b\n-|-\n1|2\n</div>") == [TokenType.TABLE, TokenType.BLANK]


def test_pipes_inside_a_code_block_are_not_a_table() -> None:
    assert one("```\na|b\n-|-\n```").type is TokenType.CODE_BLOCK


def test_a_text_line_before_the_header_stays_a_separate_token() -> None:
    tokens = tokenize("intro\na|b\n-|-")
    assert [t.type for t in tokens] == [TokenType.TEXT, TokenType.TABLE]
    assert tokens[1].line == 2


def test_two_tables_separated_by_a_blank_line() -> None:
    assert kinds("a|b\n-|-\n\nc|d\n-|-") == [TokenType.TABLE, TokenType.BLANK, TokenType.TABLE]


def test_blockquote_lines_carry_the_table_source_for_the_parser() -> None:
    inner = [t.value for t in tokenize("> a|b\n> -|-\n> 1|2")]
    assert inner == ["a|b", "-|-", "1|2"]
    assert table(NEWLINE.join(inner)).rows == (("a", "b"), ("1", "2"))


def test_table_column_limit() -> None:
    def source(columns: int) -> str:
        return "|".join(["a"] * columns) + NEWLINE + "|".join(["-"] * columns)

    assert len(table(source(MAX_TABLE_COLUMNS)).aligns) == MAX_TABLE_COLUMNS
    too_wide = source(MAX_TABLE_COLUMNS + 1)
    with pytest.raises(LexerError, match="columnas"):
        tokenize(too_wide)


def test_table_cell_limit_counts_header_and_rows() -> None:
    header = "a|" + NEWLINE + "-|" + NEWLINE
    row = "x|" + NEWLINE
    assert len(table(header + row * (MAX_TABLE_CELLS - 1)).rows) == MAX_TABLE_CELLS
    with pytest.raises(LexerError, match="celdas"):
        tokenize(header + row * MAX_TABLE_CELLS)


def test_table_cell_limit_is_shared_by_all_tables_of_the_input() -> None:
    half = "a|" + NEWLINE + "-|" + NEWLINE + ("x|" + NEWLINE) * (MAX_TABLE_CELLS // 2 - 1)
    assert len(tokenize(half + NEWLINE + half)) == 3
    with pytest.raises(LexerError, match="celdas"):
        tokenize(half + NEWLINE + half + "y|")


@pytest.mark.parametrize(
    "source",
    ["|" * 5_000, "a|" * 5_000 + NEWLINE + "-|" * 5_000, "|-" * 3_000, (chr(92) + "|") * 5_000],
)
def test_pathological_pipe_input_is_handled(source: str) -> None:
    with contextlib.suppress(LexerError):
        tokenize(source)


def test_many_pipes_in_one_row_do_not_blow_up() -> None:
    row = "|".join(["x"] * 10_000)
    token = table("a|b\n-|-\n" + row)
    assert len(token.rows[1]) == 2


# --- líneas que son solo etiquetas HTML -----------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        '<div align="center">',
        "</div>",
        "<br>",
        "<br/>",
        '<p align="center"><img src="x.png"></p>',
        "  <details><summary>",
        "<b></b>",
        "<img src=x onerror=alert(1)>",
    ],
)
def test_lines_made_only_of_html_tags_are_blank(line: str) -> None:
    assert one(line).type is TokenType.BLANK


@pytest.mark.parametrize(
    "line",
    [
        "<b>texto</b>",
        "<b>x</b> y",
        "x <b>",
        "<b> x",
        "<script>alert(1)</script>",
        "< b>",
        "<1>",
        "<>",
        "</>",
        "<b",
        "<b<i>",
        "<é>",
        "a<b>",
    ],
)
def test_lines_with_text_around_tags_are_kept_as_text(line: str) -> None:
    assert one(line).type is TokenType.TEXT


def test_html_only_line_keeps_line_numbers_of_the_following_tokens() -> None:
    tokens = tokenize('<div align="center">\ntexto\n</div>')
    assert [(t.type, t.line) for t in tokens] == [
        (TokenType.BLANK, 1),
        (TokenType.TEXT, 2),
        (TokenType.BLANK, 3),
    ]
