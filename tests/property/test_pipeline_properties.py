"""Tests de propiedades (Hypothesis) sobre el pipeline completo (spec 9.6)."""

import html
import re
import unicodedata
from collections.abc import Iterator
from html.parser import HTMLParser

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from markforge import LexerError, ParserError, convert
from markforge.ast import (
    CodeBlock,
    Emphasis,
    Image,
    Inline,
    Link,
    Strikethrough,
    Strong,
    Text,
)
from markforge.inline import MAX_INLINE_DEPTH, parse_inline
from markforge.lexer import tokenize
from markforge.parser import parse
from markforge.sanitizer import MAX_AST_DEPTH, sanitize

FRAGMENTS = [
    "# ",
    "## ",
    "#",
    "**",
    "*",
    "~~",
    "`",
    "``",
    "```",
    "```py\n",
    "[",
    "]",
    "](",
    ")",
    "![",
    "> ",
    ">",
    "- ",
    "* ",
    "+ ",
    "1. ",
    "---",
    "\n",
    "\n\n",
    " ",
    "  ",
    "\t",
    "\\",
    "&",
    "<",
    '"',
    "'",
    "a",
    "b c",
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:",
    "data:",
    "http://x.y",
    "https://a.b/c?d=1#e",
    "mailto:a@b.c",
    "//host",
    "&#106;",
    "&colon;",
    "\r\n",
    chr(0),
    chr(0x202E),
    chr(0xA0),
    chr(0x200B),
    "é",
    "日本",
]

markdown_like = st.lists(st.sampled_from(FRAGMENTS), max_size=80).map("".join)
any_text = st.one_of(st.text(max_size=300), markdown_like)
text_without_cr = any_text.filter(lambda value: "\r" not in value)

ALLOWED_TAGS = frozenset(
    {"p", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "pre", "code", "ul", "ol", "li"}
    | {"blockquote", "em", "strong", "del", "a", "img"}
)
ALLOWED_ATTRIBUTES = {"a": {"href", "rel"}, "img": {"src", "alt"}, "code": {"class"}}
LANGUAGE_CLASS = re.compile(r"language-[A-Za-z0-9_+-]{1,32}")
URL_SCHEME = re.compile(r"[a-z][a-z0-9+.-]*:")
SAFE_SCHEMES = frozenset({"http", "https", "mailto"})


def url_is_safe(value: str) -> bool:
    """Oráculo independiente del sanitizer: relativa, o esquema permitido, sin invisibles."""
    if not value or any(
        char.isspace() or unicodedata.category(char) in ("Cc", "Cf") for char in value
    ):
        return False
    match = URL_SCHEME.match(value.lower())
    return match is None or match.group()[:-1] in SAFE_SCHEMES


class SafetyChecker(HTMLParser):
    """Recorre el HTML generado y anota todo lo que no esté en la lista permitida."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.violations: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in ALLOWED_TAGS:
            self.violations.append(f"tag no permitido: {tag}")
            return
        allowed = ALLOWED_ATTRIBUTES.get(tag, set())
        for name, value in attrs:
            if name not in allowed:
                self.violations.append(f"atributo no permitido: {tag}.{name}")
            elif value is None:
                self.violations.append(f"atributo sin valor: {tag}.{name}")
            else:
                self._check_value(tag, name, value)

    def _check_value(self, tag: str, name: str, value: str) -> None:
        if name in ("href", "src") and not url_is_safe(value):
            self.violations.append(f"URL insegura en {tag}.{name}: {value!r}")
        elif name == "class" and not LANGUAGE_CLASS.fullmatch(value):
            self.violations.append(f"clase inválida: {value!r}")
        elif name == "rel" and value != "noopener noreferrer":
            self.violations.append(f"rel inválido: {value!r}")

    def handle_endtag(self, tag: str) -> None:
        if tag not in ALLOWED_TAGS:
            self.violations.append(f"tag de cierre no permitido: {tag}")

    def handle_comment(self, data: str) -> None:
        self.violations.append("comentario HTML")

    def handle_decl(self, decl: str) -> None:
        self.violations.append("declaración HTML")

    def handle_pi(self, data: str) -> None:
        self.violations.append("instrucción de procesamiento")

    def unknown_decl(self, data: str) -> None:
        self.violations.append("declaración desconocida")


def violations_of(output: str) -> list[str]:
    checker = SafetyChecker()
    checker.feed(output)
    checker.close()
    return checker.violations


def walk(node: object) -> Iterator[object]:
    yield node
    for attribute in ("children", "items"):
        for child in getattr(node, attribute, ()):
            yield from walk(child)


def depth_of(node: object) -> int:
    children = [
        child for attribute in ("children", "items") for child in getattr(node, attribute, ())
    ]
    return 1 + max((depth_of(child) for child in children), default=0)


def inline_depth(nodes: tuple[Inline, ...]) -> int:
    levels = 0
    for node in nodes:
        if isinstance(node, Emphasis | Strong | Strikethrough | Link):
            levels = max(levels, 1 + inline_depth(node.children))
    return levels


def has_forbidden_text_chars(value: str) -> bool:
    for char in value:
        code = ord(char)
        if (unicodedata.category(char) == "Cc" and char not in "\n\t") or (
            0x202A <= code <= 0x202E or 0x2066 <= code <= 0x2069
        ):
            return True
    return False


# --- convert: contrato general -------------------------------------------------------------


@given(any_text)
def test_convert_only_fails_with_lexer_or_parser_errors(text: str) -> None:
    try:
        convert(text)
    except (LexerError, ParserError):
        return


@given(any_text)
def test_convert_is_deterministic(text: str) -> None:
    try:
        first = convert(text)
    except (LexerError, ParserError):
        return
    second = convert(text)
    assert first == second


@given(text_without_cr)
def test_crlf_line_endings_give_the_same_html(text: str) -> None:
    crlf = text.replace(chr(10), chr(13) + chr(10))
    try:
        expected = convert(text)
    except (LexerError, ParserError):
        return
    assert convert(crlf) == expected


@given(st.from_regex(r"[A-Za-z]+( [A-Za-z]+)*", fullmatch=True))
def test_plain_words_become_a_single_paragraph(text: str) -> None:
    assert convert(text) == f"<p>{text}</p>\n"


@given(st.text(alphabet="<>&\"' ;#x", max_size=60))
def test_special_characters_are_escaped_exactly_once(tail: str) -> None:
    text = "x" + tail
    assert convert(text) == f"<p>{html.escape(text.strip(' '))}</p>\n"


# --- seguridad del HTML generado ------------------------------------------------------------


@given(any_text)
def test_output_html_only_contains_allowed_tags_and_safe_attributes(text: str) -> None:
    try:
        output = convert(text)
    except (LexerError, ParserError):
        assume(False)
    assert violations_of(output) == []


SCHEMES = [
    "javascript:",
    "JaVaScRiPt:",
    "data:",
    "vbscript:",
    "file:",
    "http://",
    "https://",
    "mailto:",
    "//",
    "/",
    "",
    "#",
    "?",
]
url_strategy = st.builds(
    lambda scheme, rest: scheme + rest,
    st.sampled_from(SCHEMES),
    st.text(
        alphabet=st.characters(codec="utf-8", exclude_characters=")]["),
        max_size=30,
    ),
)


@given(url_strategy)
def test_links_and_images_never_carry_unsafe_urls(url: str) -> None:
    for source in (f"[t]({url})", f"![t]({url})", f"x [a]({url}) y"):
        assert violations_of(convert(source)) == []


@given(st.text(max_size=60))
def test_code_fence_language_never_breaks_the_class_attribute(language: str) -> None:
    assume(chr(10) not in language and chr(13) not in language)
    output = convert(f"```{language}{chr(10)}code{chr(10)}```")
    assert violations_of(output) == []


# --- propiedades por etapa -------------------------------------------------------------------


@given(any_text)
def test_lexer_line_numbers_are_ordered_and_within_the_input(text: str) -> None:
    lines = text.replace(chr(13) + chr(10), chr(10)).replace(chr(13), chr(10)).count(chr(10)) + 1
    numbers = [token.line for token in tokenize(text)]
    assert numbers == sorted(numbers)
    assert all(1 <= number <= lines for number in numbers)


@given(any_text)
def test_parser_output_always_fits_the_sanitizer_depth_limit(text: str) -> None:
    try:
        document = parse(tokenize(text))
    except ParserError:
        return
    assert depth_of(document) <= MAX_AST_DEPTH


@given(any_text)
def test_inline_depth_is_bounded(text: str) -> None:
    assert inline_depth(parse_inline(text)) <= MAX_INLINE_DEPTH


@given(st.text(alphabet=st.characters(codec="utf-8", exclude_characters="\\`*~[]!")))
def test_inline_text_without_markup_is_a_single_text_node(text: str) -> None:
    expected = (Text(text),) if text else ()
    assert parse_inline(text) == expected


@given(any_text)
def test_sanitizer_is_idempotent(text: str) -> None:
    try:
        document = parse(tokenize(text))
    except ParserError:
        return
    once = sanitize(document)
    assert sanitize(once) == once


@given(any_text)
def test_sanitized_ast_has_only_safe_values(text: str) -> None:
    try:
        document = sanitize(parse(tokenize(text)))
    except ParserError:
        return
    for node in walk(document):
        if isinstance(node, Link | Image):
            assert url_is_safe(node.url)
        if isinstance(node, Text):
            assert not has_forbidden_text_chars(node.value)
        if isinstance(node, CodeBlock):
            assert node.language is None or LANGUAGE_CLASS.fullmatch("language-" + node.language)


@pytest.mark.parametrize("fragment", FRAGMENTS)
def test_every_fragment_alone_is_handled(fragment: str) -> None:
    try:
        output = convert(fragment)
    except (LexerError, ParserError):
        return
    assert violations_of(output) == []
