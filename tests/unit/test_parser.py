import pytest

from markforge.ast import (
    BlockQuote,
    CodeBlock,
    Document,
    Heading,
    HorizontalRule,
    List,
    ListItem,
    Paragraph,
    Strong,
    Text,
)
from markforge.errors import ParserError
from markforge.lexer import Token, TokenType, tokenize
from markforge.parser import MAX_NESTING_DEPTH, parse


def doc(source: str) -> Document:
    return parse(tokenize(source))


def para(text: str) -> Paragraph:
    return Paragraph((Text(text),))


def item(text: str) -> ListItem:
    return ListItem((para(text),))


def test_empty_input_is_empty_document() -> None:
    assert doc("") == Document(())
    assert doc("\n\n  \n") == Document(())


def test_heading() -> None:
    assert doc("## Título").children == (Heading(2, (Text("Título"),)),)


def test_empty_heading_has_no_children() -> None:
    assert doc("#").children == (Heading(1, ()),)


def test_horizontal_rule() -> None:
    assert doc("---").children == (HorizontalRule(),)


def test_code_block() -> None:
    assert doc("```py\nx = 1\n```").children == (CodeBlock("x = 1", "py"),)
    assert doc("```\n```").children == (CodeBlock("", None),)


def test_paragraph_joins_consecutive_lines() -> None:
    assert doc("uno\ndos").children == (para("uno\ndos"),)


def test_blank_line_splits_paragraphs() -> None:
    assert doc("uno\n\ndos").children == (para("uno"), para("dos"))


@pytest.mark.parametrize("interrupter", ["# h", "---", "> q", "- item", "1. item", "```\nx\n```"])
def test_paragraph_is_interrupted_by_blocks(interrupter: str) -> None:
    children = doc("texto\n" + interrupter).children
    assert children[0] == para("texto")
    assert len(children) == 2


def test_unordered_list() -> None:
    assert doc("- a\n- b").children == (List(False, (item("a"), item("b"))),)


def test_ordered_list() -> None:
    assert doc("1. a\n2. b").children == (List(True, (item("a"), item("b"))),)


def test_blank_lines_between_items_keep_one_list() -> None:
    assert doc("- a\n\n- b").children == (List(False, (item("a"), item("b"))),)


def test_changing_list_kind_starts_a_new_list() -> None:
    assert doc("- a\n1. b").children == (List(False, (item("a"),)), List(True, (item("b"),)))


def test_list_ends_at_other_block() -> None:
    assert doc("- a\ntexto").children == (List(False, (item("a"),)), para("texto"))
    assert doc("- a\n\ntexto").children == (List(False, (item("a"),)), para("texto"))


def test_empty_list_item_has_no_children() -> None:
    assert doc("-").children == (List(False, (ListItem(()),)),)


def test_blockquote_groups_consecutive_lines() -> None:
    assert doc("> a\n> b").children == (BlockQuote((para("a\nb"),)),)


def test_blockquote_blank_marker_splits_paragraphs() -> None:
    assert doc("> a\n>\n> b").children == (BlockQuote((para("a"), para("b"))),)


def test_blockquote_contains_blocks() -> None:
    expected = BlockQuote(
        (Heading(1, (Text("t"),)), List(False, (item("x"),)), CodeBlock("c", None))
    )
    assert doc("> # t\n> - x\n> ```\n> c\n> ```").children == (expected,)


def test_nested_blockquote() -> None:
    assert doc("> > hondo").children == (BlockQuote((BlockQuote((para("hondo"),)),)),)


def test_separate_blockquotes() -> None:
    assert doc("> a\n\n> b").children == (BlockQuote((para("a"),)), BlockQuote((para("b"),)))


def test_blockquote_ends_at_unquoted_line() -> None:
    assert doc("> a\ntexto").children == (BlockQuote((para("a"),)), para("texto"))


def test_list_and_blockquote_are_adjacent_blocks() -> None:
    assert doc("- a\n> q").children == (List(False, (item("a"),)), BlockQuote((para("q"),)))


def test_blockquote_list_then_paragraph() -> None:
    expected = BlockQuote((List(False, (item("a"), item("b"))), para("t")))
    assert doc("> - a\n> - b\n>\n> t").children == (expected,)


def test_nesting_at_limit_is_accepted() -> None:
    assert doc(">" * MAX_NESTING_DEPTH + " x").children


def test_nesting_over_limit_raises() -> None:
    with pytest.raises(ParserError, match="anidada"):
        doc(">" * (MAX_NESTING_DEPTH + 1) + " x")


def test_deep_nesting_does_not_hit_recursion_limit() -> None:
    with pytest.raises(ParserError):
        doc(">" * 50_000)


def test_inline_markup_is_parsed_in_blocks() -> None:
    strong = Paragraph((Strong((Text("a"),)),))
    assert doc("**a**").children == (strong,)
    assert doc("# **a**").children == (Heading(1, (Strong((Text("a"),)),)),)
    assert doc("- **a**").children == (List(False, (ListItem((strong,)),)),)


def test_parse_accepts_any_token_sequence() -> None:
    tokens = [Token(TokenType.TEXT, "a", 1), Token(TokenType.BLANK, "", 2)]
    assert parse(tokens) == Document((para("a"),))


def test_mixed_document() -> None:
    result = doc("# T\n\npárrafo\n\n- a\n- b\n\n> q\n\n---\n")
    assert result.children == (
        Heading(1, (Text("T"),)),
        para("párrafo"),
        List(False, (item("a"), item("b"))),
        BlockQuote((para("q"),)),
        HorizontalRule(),
    )


def test_indented_sublist_is_flattened_for_now() -> None:
    assert doc("- a\n  - b").children == (List(False, (item("a"), item("b"))),)
