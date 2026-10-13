from typing import cast

import pytest

from markforge.ast import (
    Block,
    BlockQuote,
    CodeBlock,
    Document,
    Emphasis,
    Heading,
    HorizontalRule,
    Image,
    Inline,
    InlineCode,
    Link,
    List,
    ListItem,
    Paragraph,
    Strikethrough,
    Strong,
    Text,
)
from markforge.errors import RenderError
from markforge.renderer import MAX_RENDER_DEPTH, render


def t(value: str) -> Text:
    return Text(value)


def html(*blocks: Block) -> str:
    return render(Document(blocks))


def para(*children: Inline) -> Paragraph:
    return Paragraph(children)


def test_empty_document_renders_empty_string() -> None:
    assert render(Document(())) == ""


def test_paragraph() -> None:
    assert html(para(t("hola"))) == "<p>hola</p>\n"


def test_blocks_are_separated_by_newlines() -> None:
    assert html(para(t("a")), para(t("b"))) == "<p>a</p>\n<p>b</p>\n"


@pytest.mark.parametrize("level", range(1, 7))
def test_headings(level: int) -> None:
    assert html(Heading(level, (t("T"),))) == f"<h{level}>T</h{level}>\n"


def test_horizontal_rule() -> None:
    assert html(HorizontalRule()) == "<hr>\n"


def test_inline_formatting() -> None:
    node = para(
        Emphasis((t("e"),)),
        Strong((t("s"),)),
        Strikethrough((t("d"),)),
        InlineCode("c"),
    )
    assert html(node) == "<p><em>e</em><strong>s</strong><del>d</del><code>c</code></p>\n"


def test_nested_inline() -> None:
    node = para(Strong((t("a "), Emphasis((t("b"),)))))
    assert html(node) == "<p><strong>a <em>b</em></strong></p>\n"


def test_link_has_noopener_noreferrer() -> None:
    node = para(Link("https://a.b/x", (t("txt"),)))
    assert html(node) == '<p><a href="https://a.b/x" rel="noopener noreferrer">txt</a></p>\n'


def test_image() -> None:
    node = para(Image("https://a.b/i.png", "alt"))
    assert html(node) == '<p><img src="https://a.b/i.png" alt="alt"></p>\n'


def test_code_block_with_and_without_language() -> None:
    assert html(CodeBlock("x = 1", "python")) == (
        '<pre><code class="language-python">x = 1\n</code></pre>\n'
    )
    assert html(CodeBlock("x", None)) == "<pre><code>x\n</code></pre>\n"
    assert html(CodeBlock("", None)) == "<pre><code></code></pre>\n"


def test_tight_lists() -> None:
    items = (ListItem((para(t("a")),)), ListItem((para(t("b")),)))
    assert html(List(False, items)) == "<ul>\n<li>a</li>\n<li>b</li>\n</ul>\n"
    assert html(List(True, items)) == "<ol>\n<li>a</li>\n<li>b</li>\n</ol>\n"


def test_empty_list_item() -> None:
    assert html(List(False, (ListItem(()),))) == "<ul>\n<li></li>\n</ul>\n"


def test_list_item_with_several_blocks() -> None:
    item = ListItem((para(t("a")), CodeBlock("c", None)))
    expected = "<ul>\n<li>\n<p>a</p>\n<pre><code>c\n</code></pre>\n</li>\n</ul>\n"
    assert html(List(False, (item,))) == expected


def test_blockquote() -> None:
    assert html(BlockQuote((para(t("q")),))) == "<blockquote>\n<p>q</p>\n</blockquote>\n"
    assert html(BlockQuote(())) == "<blockquote>\n</blockquote>\n"


def test_nested_blockquote() -> None:
    node = BlockQuote((BlockQuote((para(t("x")),)),))
    expected = "<blockquote>\n<blockquote>\n<p>x</p>\n</blockquote>\n</blockquote>\n"
    assert html(node) == expected


def test_soft_line_breaks_are_kept() -> None:
    assert html(para(t("a\nb"))) == "<p>a\nb</p>\n"


ATTACK = "<script>alert(1)</script>"
QUOTES = "\"'&<>"
ESCAPED_QUOTES = "&quot;&#x27;&amp;&lt;&gt;"


def test_text_is_escaped() -> None:
    assert html(para(t(ATTACK))) == "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>\n"
    assert html(para(t(QUOTES))) == f"<p>{ESCAPED_QUOTES}</p>\n"


def test_inline_code_and_code_block_are_escaped() -> None:
    assert (
        html(para(InlineCode(ATTACK)))
        == "<p><code>&lt;script&gt;alert(1)&lt;/script&gt;</code></p>\n"
    )
    assert html(CodeBlock(ATTACK, None)) == (
        "<pre><code>&lt;script&gt;alert(1)&lt;/script&gt;\n</code></pre>\n"
    )


def test_attribute_values_are_escaped() -> None:
    url = 'https://a.b/"onmouseover="alert(1)'
    result = html(para(Link(url, (t("x"),)), Image(url, QUOTES)))
    assert '"onmouseover=' not in result
    assert "&quot;onmouseover=&quot;" in result
    assert f'alt="{ESCAPED_QUOTES}"' in result


def test_entity_like_urls_are_escaped_once() -> None:
    result = html(para(Link("&#106;avascript:x", (t("x"),))))
    assert 'href="&amp;#106;avascript:x"' in result


def test_text_that_looks_like_an_entity_is_escaped() -> None:
    assert html(para(t("&amp; &lt;"))) == "<p>&amp;amp; &amp;lt;</p>\n"


def test_language_is_escaped_in_the_class() -> None:
    result = html(CodeBlock("x", 'a"b'))
    assert result == '<pre><code class="language-a&quot;b">x\n</code></pre>\n'


def test_invalid_heading_level_raises() -> None:
    heading = Heading(1, ())
    object.__setattr__(heading, "level", 9)
    with pytest.raises(RenderError, match="fuera de rango"):
        html(heading)


@pytest.mark.parametrize("fake", [object(), "texto", None])
def test_unknown_block_raises(fake: object) -> None:
    block = cast(Block, fake)
    with pytest.raises(RenderError, match="nodo desconocido"):
        html(block)


@pytest.mark.parametrize("fake", [object(), "texto", None])
def test_unknown_inline_raises(fake: object) -> None:
    block = para(cast(Inline, fake))
    with pytest.raises(RenderError, match="nodo desconocido"):
        html(block)


def test_unknown_list_item_raises() -> None:
    block = List(False, (cast(ListItem, object()),))
    with pytest.raises(RenderError, match="nodo desconocido"):
        html(block)


def test_block_depth_over_limit_raises() -> None:
    node: Block = para(t("x"))
    for _ in range(MAX_RENDER_DEPTH + 1):
        node = BlockQuote((node,))
    with pytest.raises(RenderError, match="profundidad"):
        html(node)


def test_inline_depth_over_limit_raises() -> None:
    inline: Inline = t("x")
    for _ in range(MAX_RENDER_DEPTH + 1):
        inline = Emphasis((inline,))
    block = para(inline)
    with pytest.raises(RenderError, match="profundidad"):
        html(block)


def test_list_item_depth_over_limit_raises() -> None:
    node: Block = para(t("x"))
    for _ in range(MAX_RENDER_DEPTH):
        node = List(False, (ListItem((node,)),))
    with pytest.raises(RenderError, match="profundidad"):
        html(node)


def test_depth_within_limit_is_rendered() -> None:
    node: Block = para(t("x"))
    for _ in range(MAX_RENDER_DEPTH - 2):
        node = BlockQuote((node,))
    assert html(node).count("<blockquote>") == MAX_RENDER_DEPTH - 2


def test_large_document_renders_without_quadratic_time() -> None:
    blocks = tuple(para(t("a")) for _ in range(50_000))
    assert render(Document(blocks)).count("<p>") == 50_000


@pytest.mark.parametrize("level", [True, 1.5, "1"])
def test_non_int_heading_level_raises(level: object) -> None:
    heading = Heading(1, ())
    object.__setattr__(heading, "level", level)
    with pytest.raises(RenderError, match="fuera de rango"):
        html(heading)
