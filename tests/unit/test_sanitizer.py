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
    Text,
)
from markforge.errors import SanitizationError
from markforge.sanitizer import (
    ALLOWED_SCHEMES,
    MAX_AST_DEPTH,
    MAX_LANGUAGE_LENGTH,
    MAX_URL_LENGTH,
    is_safe_url,
    sanitize,
)


def t(value: str) -> Text:
    return Text(value)


def clean(*blocks: Block) -> tuple[Block, ...]:
    return sanitize(Document(blocks)).children


def para(*children: Inline) -> Paragraph:
    return Paragraph(children)


SAFE_URLS = [
    "http://a.b",
    "https://a.b/x?y=1#z",
    "HTTPS://A.B",
    "mailto:a@b.c",
    "//a.b/x",
    "/ruta",
    "./x",
    "../x",
    "x/y:z",
    "#ancla",
    "?q=1:2",
    "pagina.html",
    "javascript&colon;alert(1)",
    "&#106;avascript:alert(1)",
]

UNSAFE_URLS = [
    chr(92) * 2 + "evil.com",
    "/" + chr(92) + "evil.com",
    "x" + chr(92) + "y",
    "",
    "javascript:alert(1)",
    "JaVaScRiPt:alert(1)",
    " javascript:alert(1)",
    "java\tscript:alert(1)",
    "java\nscript:alert(1)",
    "\x01javascript:alert(1)",
    "\x00javascript:alert(1)",
    "java" + chr(0x200B) + "script:alert(1)",
    chr(0xA0) + "javascript:alert(1)",
    chr(0x2028) + "javascript:alert(1)",
    "javascript" + chr(0xFEFF) + ":alert(1)",
    "javascript\x1f:alert(1)",
    "DATA:text/html;base64,PHNjcmlwdD4=",
    "VbScript:msgbox(1)",
    "javascript:alert(1)//http://a.b",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
    "ftp://a.b",
    "java<script>:x",
    ":x",
    "a:b",
    "http://a.b/ x",
    "http://" + "a" * MAX_URL_LENGTH,
]


@pytest.mark.parametrize("url", SAFE_URLS)
def test_safe_urls(url: str) -> None:
    assert is_safe_url(url)


@pytest.mark.parametrize("url", UNSAFE_URLS)
def test_unsafe_urls(url: str) -> None:
    assert not is_safe_url(url)


def test_url_at_length_limit_is_safe() -> None:
    assert is_safe_url("/" + "a" * (MAX_URL_LENGTH - 1))


def test_allowed_schemes_are_a_whitelist() -> None:
    assert {"http", "https", "mailto"} == ALLOWED_SCHEMES


def test_safe_link_is_kept() -> None:
    node = Link("https://a.b", (t("x"),))
    assert clean(para(node)) == (para(node),)


def test_unsafe_link_is_replaced_by_its_content() -> None:
    node = Link("javascript:alert(1)", (Strong((t("x"),)), t(" y")))
    assert clean(para(node)) == (para(Strong((t("x"),)), t(" y")),)


def test_text_around_unsafe_link_is_merged() -> None:
    node = Link("data:x", (t("b"),))
    assert clean(para(t("a "), node, t(" c"))) == (para(t("a b c")),)


def test_unsafe_link_with_unsafe_link_inside() -> None:
    inner = Link("vbscript:x", (t("deep"),))
    outer = Link("javascript:x", (inner,))
    assert clean(para(outer)) == (para(t("deep")),)


def test_safe_image_is_kept() -> None:
    node = Image("https://a.b/i.png", "alt")
    assert clean(para(node)) == (para(node),)


def test_unsafe_image_becomes_alt_text() -> None:
    assert clean(para(Image("javascript:x", "alt"))) == (para(t("alt")),)


def test_unsafe_image_alt_is_cleaned_and_merged_with_neighbours() -> None:
    node = Image("javascript:x", "b" + chr(0) + "c")
    assert clean(para(t("a"), node, t("d"))) == (para(t("abcd")),)


def test_unsafe_link_inside_unsafe_image_context_keeps_no_url() -> None:
    result = clean(para(Link("data:x", (Image("vbscript:y", "alt"),))))
    assert result == (para(t("alt")),)


def test_unsafe_image_without_alt_disappears() -> None:
    assert clean(para(Image("data:x", ""))) == (para(),)


def test_formatting_nodes_are_sanitized_recursively() -> None:
    bad = Link("javascript:x", (t("x"),))
    result = clean(para(Emphasis((bad,)), Strong((bad,)), Strikethrough((bad,))))
    assert result == (para(Emphasis((t("x"),)), Strong((t("x"),)), Strikethrough((t("x"),))),)


def test_blocks_are_sanitized_recursively() -> None:
    bad = para(Link("javascript:x", (t("x"),)))
    good = para(t("x"))
    result = clean(
        Heading(2, (Link("javascript:x", (t("h"),)),)),
        BlockQuote((bad,)),
        List(True, (ListItem((bad,)), ListItem(()))),
        HorizontalRule(),
    )
    assert result == (
        Heading(2, (t("h"),)),
        BlockQuote((good,)),
        List(True, (ListItem((good,)), ListItem(()))),
        HorizontalRule(),
    )


def test_control_characters_are_removed() -> None:
    nul, bell, esc, c1 = chr(0), chr(7), chr(27), chr(0x85)
    result = clean(
        para(t("a" + nul + "b"), InlineCode("c" + bell + "d"), Image("/i", "e" + esc + "f")),
        CodeBlock("g" + c1 + "h", None),
    )
    assert result == (
        para(t("ab"), InlineCode("cd"), Image("/i", "ef")),
        CodeBlock("gh", None),
    )


def test_newlines_and_tabs_are_kept() -> None:
    assert clean(CodeBlock("a\n\tb", None)) == (CodeBlock("a\n\tb", None),)


def test_text_made_only_of_control_chars_disappears() -> None:
    assert clean(para(t(chr(0)))) == (para(),)


def test_html_is_not_escaped_here() -> None:
    node = para(t('<script>alert(1)</script> & "q"'), InlineCode("<b>"))
    assert clean(node) == (node,)


@pytest.mark.parametrize("language", ["python", "c++", "objective-c", "a_b", "X9", "a" * 32])
def test_valid_languages_are_kept(language: str) -> None:
    assert clean(CodeBlock("x", language)) == (CodeBlock("x", language),)


@pytest.mark.parametrize(
    "language",
    ["", "a b", 'x"onload=', "<script>", "a/b", "é", "a" * (MAX_LANGUAGE_LENGTH + 1), "a.b"],
)
def test_invalid_languages_are_dropped(language: str) -> None:
    assert clean(CodeBlock("x", language)) == (CodeBlock("x", None),)


def test_missing_language_stays_missing() -> None:
    assert clean(CodeBlock("x", None)) == (CodeBlock("x", None),)


def test_sanitize_does_not_modify_the_input() -> None:
    original = Document((para(Link("javascript:x", (t("x"),))),))
    sanitize(original)
    assert original == Document((para(Link("javascript:x", (t("x"),))),))


def test_sanitize_is_idempotent() -> None:
    document = Document(
        (para(Link("javascript:x", (t("x"),)), Image("data:y", "z"), t("a" + chr(0))),)
    )
    once = sanitize(document)
    assert sanitize(once) == once


def test_empty_document() -> None:
    assert sanitize(Document(())) == Document(())


def test_block_nesting_within_limit_is_accepted() -> None:
    node: Block = para(t("x"))
    for _ in range(MAX_AST_DEPTH - 2):
        node = BlockQuote((node,))
    assert clean(node)


def test_block_nesting_over_limit_raises() -> None:
    node: Block = para(t("x"))
    for _ in range(MAX_AST_DEPTH + 1):
        node = BlockQuote((node,))
    with pytest.raises(SanitizationError, match="profundidad"):
        clean(node)


def test_inline_nesting_over_limit_raises() -> None:
    node: Inline = t("x")
    for _ in range(MAX_AST_DEPTH + 1):
        node = Emphasis((node,))
    with pytest.raises(SanitizationError, match="profundidad"):
        clean(para(node))


def test_very_deep_ast_raises_instead_of_recursion_error() -> None:
    node: Block = para(t("x"))
    for _ in range(5_000):
        node = BlockQuote((node,))
    with pytest.raises(SanitizationError):
        clean(node)


def test_list_item_depth_is_checked() -> None:
    node: Block = para(t("x"))
    for _ in range(MAX_AST_DEPTH):
        node = List(False, (ListItem((node,)),))
    with pytest.raises(SanitizationError, match="profundidad"):
        clean(node)


@pytest.mark.parametrize("fake", [object(), "texto", 42, None])
def test_unknown_block_is_rejected(fake: object) -> None:
    with pytest.raises(SanitizationError, match="nodo desconocido"):
        clean(cast(Block, fake))


@pytest.mark.parametrize("fake", [object(), "texto", None])
def test_unknown_inline_is_rejected(fake: object) -> None:
    with pytest.raises(SanitizationError, match="nodo desconocido"):
        clean(para(cast(Inline, fake)))


def test_unknown_list_item_is_rejected() -> None:
    fake = cast(Any, List(False, (cast(ListItem, object()),)))
    with pytest.raises(SanitizationError, match="nodo desconocido"):
        clean(fake)


def test_bidi_overrides_are_removed_from_text() -> None:
    bidi = "".join(chr(code) for code in (0x202A, 0x202E, 0x2066, 0x2069))
    assert clean(para(t("a" + bidi + "b"))) == (para(t("ab")),)


def test_many_adjacent_text_nodes_are_merged_in_linear_time() -> None:
    result = clean(para(*[t("a")] * 200_000))
    assert result == (para(t("a" * 200_000)),)
