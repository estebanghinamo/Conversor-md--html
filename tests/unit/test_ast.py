import dataclasses
from typing import cast

import pytest

from markforge.ast import (
    BlockQuote,
    CodeBlock,
    Document,
    Emphasis,
    Heading,
    HorizontalRule,
    Image,
    InlineCode,
    Link,
    List,
    ListItem,
    Paragraph,
    Strikethrough,
    Strong,
    Text,
)


def test_builds_nested_document() -> None:
    doc = Document(
        (
            Heading(1, (Text("Título"),)),
            Paragraph((Text("a "), Strong((Text("b"),)), Emphasis((Text("c"),)))),
            List(False, (ListItem((Paragraph((Text("x"),)),)),)),
            BlockQuote((Paragraph((Text("q"),)),)),
            HorizontalRule(),
            CodeBlock("print(1)", "python"),
        )
    )
    assert len(doc.children) == 6
    assert isinstance(doc.children[1], Paragraph)
    assert doc.children[1].children[1] == Strong((Text("b"),))


def test_inline_nodes_hold_data() -> None:
    assert Link("https://a.b", (Text("x"),)).url == "https://a.b"
    assert Image("https://a.b/i.png", "alt").alt == "alt"
    assert InlineCode("x").value == "x"
    assert Strikethrough((Text("x"),)).children == (Text("x"),)


def test_code_block_language_is_optional() -> None:
    assert CodeBlock("x").language is None


@pytest.mark.parametrize("level", [1, 6])
def test_heading_accepts_valid_levels(level: int) -> None:
    assert Heading(level, ()).level == level


@pytest.mark.parametrize("level", [0, 7, -1])
def test_heading_rejects_invalid_levels(level: int) -> None:
    with pytest.raises(ValueError, match="fuera de rango"):
        Heading(level, ())


def test_nodes_are_immutable() -> None:
    text = Text("a")
    with pytest.raises(dataclasses.FrozenInstanceError):
        text.value = "b"  # type: ignore[misc]


def test_nodes_compare_by_value() -> None:
    first = Paragraph((Text("a"),))
    second = Paragraph((Text("a"),))
    assert first == second
    assert first != Paragraph((Text("b"),))


def test_empty_document_and_horizontal_rule() -> None:
    assert Document(()).children == ()
    rule = HorizontalRule()
    assert rule == HorizontalRule()


def test_nodes_are_hashable_and_usable_in_sets() -> None:
    doc = Document((Paragraph((Text("a"), Link("https://a.b", (Text("x"),)))),))
    assert hash(doc) == hash(Document((Paragraph((Text("a"), Link("https://a.b", (Text("x"),)))),)))
    assert len({Text("a"), Text("a"), Text("b")}) == 2


def test_nodes_use_slots() -> None:
    assert not hasattr(Text("a"), "__dict__")


def test_heading_is_immutable_after_validation() -> None:
    heading = Heading(2, ())
    with pytest.raises(dataclasses.FrozenInstanceError):
        heading.level = 9  # type: ignore[misc]


def test_different_node_types_with_same_data_are_not_equal() -> None:
    assert cast(object, Text("a")) != InlineCode("a")
    assert cast(object, Emphasis((Text("a"),))) != Strong((Text("a"),))


def test_deeply_nested_blockquotes() -> None:
    node: BlockQuote = BlockQuote(())
    for _ in range(50):
        node = BlockQuote((node,))
    assert isinstance(node.children[0], BlockQuote)


@pytest.mark.parametrize("level", [True, 1.0, "1"])
def test_heading_rejects_non_int_levels(level: object) -> None:
    invalid_level = cast(int, level)
    with pytest.raises(ValueError, match="fuera de rango"):
        Heading(invalid_level, ())
