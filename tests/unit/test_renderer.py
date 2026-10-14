from typing import Any, cast

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
    Table,
    TableCell,
    TableRow,
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


def cell(*children: Inline) -> TableCell:
    return TableCell(children)


def row(*cells: TableCell) -> TableRow:
    return TableRow(cells)


def test_table_with_header_and_body() -> None:
    table = Table(
        (None, None),
        row(cell(t("a")), cell(t("b"))),
        (row(cell(t("1")), cell(t("2"))), row(cell(t("3")), cell(t("4")))),
    )
    assert html(table) == (
        "<table>\n"
        "<thead>\n"
        "<tr><th>a</th><th>b</th></tr>\n"
        "</thead>\n"
        "<tbody>\n"
        "<tr><td>1</td><td>2</td></tr>\n"
        "<tr><td>3</td><td>4</td></tr>\n"
        "</tbody>\n"
        "</table>\n"
    )


def test_table_without_rows_has_no_tbody() -> None:
    table = Table((None,), row(cell(t("a"))), ())
    assert html(table) == "<table>\n<thead>\n<tr><th>a</th></tr>\n</thead>\n</table>\n"


def test_table_alignments_apply_to_header_and_body_cells() -> None:
    table = Table(
        ("left", "center", "right", None),
        row(cell(t("a")), cell(t("b")), cell(t("c")), cell(t("d"))),
        (row(cell(t("1")), cell(t("2")), cell(t("3")), cell(t("4"))),),
    )
    assert html(table) == (
        "<table>\n<thead>\n"
        '<tr><th align="left">a</th><th align="center">b</th>'
        '<th align="right">c</th><th>d</th></tr>\n'
        "</thead>\n<tbody>\n"
        '<tr><td align="left">1</td><td align="center">2</td>'
        '<td align="right">3</td><td>4</td></tr>\n'
        "</tbody>\n</table>\n"
    )


def test_table_cells_render_inline_markup_and_escape_text() -> None:
    table = Table(
        (None, None),
        row(cell(Strong((t("a"),))), cell(t("<b>&"))),
        (row(cell(Link("/u", (t("x"),))), cell(InlineCode("<i>"), Image("/i.png", '"'))),),
    )
    output = html(table)
    assert "<th><strong>a</strong></th><th>&lt;b&gt;&amp;</th>" in output
    assert (
        '<td><a href="/u" rel="noopener noreferrer">x</a></td>'
        '<td><code>&lt;i&gt;</code><img src="/i.png" alt="&quot;"></td>'
    ) in output
    assert "<b>" not in output
    assert "<i>" not in output


def test_empty_cell_renders_empty_element() -> None:
    table = Table((None,), row(cell()), (row(cell()),))
    assert "<tr><th></th></tr>" in html(table)
    assert "<tr><td></td></tr>" in html(table)


def test_table_between_other_blocks() -> None:
    table = Table((None,), row(cell(t("a"))), ())
    assert html(para(t("x")), table).startswith("<p>x</p>\n<table>\n")


@pytest.mark.parametrize("align", ["justify", "LEFT", '" onclick="x', 1, True])
def test_invalid_alignment_raises(align: object) -> None:
    table = Table((cast(Any, align),), row(cell(t("a"))), ())
    with pytest.raises(RenderError, match="alineación"):
        html(table)


@pytest.mark.parametrize("width", [0, 1, 3])
def test_row_with_wrong_width_raises(width: int) -> None:
    header = Table((None, None), row(*[cell()] * width), ())
    with pytest.raises(RenderError, match="celdas"):
        html(header)
    body = Table((None, None), row(cell(), cell()), (row(*[cell()] * width),))
    with pytest.raises(RenderError, match="celdas"):
        html(body)


@pytest.mark.parametrize("fake", [object(), "texto", None])
def test_unknown_table_row_and_cell_raise(fake: object) -> None:
    with pytest.raises(RenderError, match="nodo desconocido"):
        html(Table((None,), cast(TableRow, fake), ()))
    with pytest.raises(RenderError, match="nodo desconocido"):
        html(Table((None,), row(cast(TableCell, fake)), ()))


@pytest.mark.parametrize(
    ("levels", "content", "accepted"),
    [
        (60, (t("x"),), True),
        (61, (t("x"),), False),
        (61, (), True),
        (62, (), False),
        (63, (), False),
        (64, (), False),
    ],
)
def test_table_depth_is_checked_in_block_row_cell_and_inline(
    levels: int, content: tuple[Inline, ...], accepted: bool
) -> None:
    node: Block = Table((None,), row(cell(*content)), ())
    for _ in range(levels):
        node = BlockQuote((node,))
    if accepted:
        assert "<table>" in html(node)
    else:
        with pytest.raises(RenderError, match="profundidad"):
            html(node)


def test_large_document_renders_without_quadratic_time() -> None:
    blocks = tuple(para(t("a")) for _ in range(50_000))
    assert render(Document(blocks)).count("<p>") == 50_000


@pytest.mark.parametrize("level", [True, 1.5, "1"])
def test_non_int_heading_level_raises(level: object) -> None:
    heading = Heading(1, ())
    object.__setattr__(heading, "level", level)
    with pytest.raises(RenderError, match="fuera de rango"):
        html(heading)
