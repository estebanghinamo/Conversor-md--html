"""Tests de propiedades (Hypothesis) sobre el pipeline completo (spec 9.6)."""

import html
import re
import unicodedata
from collections.abc import Iterator
from html.parser import HTMLParser

import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st

from markforge import LexerError, ParserError, SanitizationError, convert
from markforge.ast import (
    Block,
    BlockQuote,
    CodeBlock,
    Document,
    Emphasis,
    Image,
    Inline,
    InlineCode,
    Link,
    Paragraph,
    Strikethrough,
    Strong,
    Text,
)
from markforge.inline import MAX_INLINE_DEPTH, parse_inline
from markforge.lexer import tokenize
from markforge.parser import parse
from markforge.renderer import render
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
    "|",
    " | ",
    "|:--|--:|",
    "-|-",
    "\\|",
    '<div align="center">',
    "</div>",
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
    "\r",
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
    | {"table", "thead", "tbody", "tr", "th", "td"}
)
ALLOWED_ATTRIBUTES = {
    "a": {"href", "rel"},
    "img": {"src", "alt"},
    "code": {"class"},
    "th": {"align"},
    "td": {"align"},
}
ALIGN_VALUES = frozenset({"left", "center", "right"})
LANGUAGE_CLASS = re.compile(r"language-[A-Za-z0-9_+-]{1,32}")
LANGUAGE_NAME = re.compile(r"[A-Za-z0-9_+-]{1,32}")
SAFE_SCHEMES = frozenset({"http", "https", "mailto"})


def url_is_safe(value: str) -> bool:
    """Oráculo independiente del sanitizer: relativa o esquema permitido; sin invisibles."""
    if not value or len(value) > 2048 or "\\" in value:
        return False
    if any(char.isspace() or unicodedata.category(char) in ("Cc", "Cf") for char in value):
        return False
    head = re.split(r"[/?#]", value, maxsplit=1)[0]
    return ":" not in head or head.split(":", 1)[0].lower() in SAFE_SCHEMES


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
        elif name == "align" and value not in ALIGN_VALUES:
            self.violations.append(f"align inválido: {value!r}")

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


pipe_text = st.lists(
    st.sampled_from(
        ["|", "\\|", " ", "-", ":", "a", "b", "\n", "<b>", "&", '"', "*", "`", "[x](/u)"]
    ),
    max_size=60,
).map("".join)


@given(pipe_text)
def test_text_with_pipes_never_breaks_or_emits_unescaped_html(text: str) -> None:
    output = convert(text)
    assert violations_of(output) == []
    assert "<b>" not in output


@given(
    st.lists(st.from_regex(r"[a-z]{0,4}", fullmatch=True), min_size=1, max_size=6),
    st.lists(st.lists(st.from_regex(r"[a-z]{0,4}", fullmatch=True), max_size=8), max_size=5),
)
def test_every_table_row_has_as_many_cells_as_the_header(
    header: list[str], body: list[list[str]]
) -> None:
    columns = len(header)
    lines = ["|" + "|".join(header) + "|", "|" + "|".join(["---"] * columns) + "|"]
    lines += ["|" + "|".join(cells) + "|" for cells in body]
    output = convert(chr(10).join(lines))
    rows = [line for line in output.split(chr(10)) if line.startswith("<tr>")]
    assert len(rows) == 1 + len(body)
    for line in rows:
        assert line.count("</th>") + line.count("</td>") == columns


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


# --- fortaleza: escape del renderer (round-trip contra un parser HTML) ------------------------

NASTY_CODES = (0, 8, 9, 10, 11, 13, 31, 32, 126, 127, 159, 160, 173, 0x2029, 0x202A, 0x202E)
NASTY_CODES_MORE = (0x202F, 0x2065, 0x2066, 0x2069, 0x206A, 0x200B, 0xFEFF)
NASTY_CHARS = [chr(code) for code in (*NASTY_CODES, *NASTY_CODES_MORE)] + list("<>&\"'`=/\\:;#?")
MARKUP_PIECES = ["<b>", "</code>", "<script>", "&amp;", "&lt;", "&#60;", '" x="', "'>", "<!--"]
nasty_piece = st.one_of(st.characters(), st.sampled_from(NASTY_CHARS + MARKUP_PIECES))
nasty_text = st.lists(nasty_piece, max_size=30).map("".join)


class Collector(HTMLParser):
    """Registra etiquetas (con atributos ya des-escapados) y texto del HTML generado."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.starts: list[tuple[str, list[tuple[str, str | None]]]] = []
        self.data: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.starts.append((tag, attrs))

    def handle_data(self, data: str) -> None:
        self.data.append(data)


def collect(output: str) -> Collector:
    collector = Collector()
    collector.feed(output)
    collector.close()
    return collector


@example('"><script>', '" onerror="x', "<b>", "<script>&amp;")
@given(nasty_text, nasty_text, nasty_text, nasty_text)
def test_renderer_escapes_attributes_and_text_so_they_round_trip(
    url: str, alt: str, label: str, code: str
) -> None:
    paragraph = Paragraph((Link(url, (Text(label),)), Image(url, alt), InlineCode(code)))
    collector = collect(render(Document((paragraph,))))
    assert collector.starts == [
        ("p", []),
        ("a", [("href", url), ("rel", "noopener noreferrer")]),
        ("img", [("src", url), ("alt", alt)]),
        ("code", []),
    ]
    assert "".join(collector.data) == label + code + "\n"


@example("<script>x</script>", 'a"><script>')
@given(nasty_text, st.one_of(st.none(), nasty_text))
def test_renderer_escapes_code_block_content_and_language(code: str, language: str | None) -> None:
    collector = collect(render(Document((CodeBlock(code, language),))))
    attributes = [("class", "language-" + language)] if language else []
    assert collector.starts == [("pre", []), ("code", attributes)]
    assert "".join(collector.data) == (code + "\n" if code else "") + "\n"


@given(nasty_text)
def test_pipeline_escapes_image_alt_and_code_block_content(payload: str) -> None:
    safe = payload.translate({ord(char): None for char in "[]()\\*_~!`\n\r"}).strip(" \t")
    assume(safe == clean_text(safe))
    image = collect(convert(f"![{safe}](/u)"))
    assert image.starts == [("p", []), ("img", [("src", "/u"), ("alt", safe)])]
    code = collect(convert(f"```{chr(10)}{safe}{chr(10)}```"))
    assert code.starts == [("pre", []), ("code", [])]
    assert "".join(code.data) == (safe + "\n" if safe else "") + "\n"


# --- fortaleza: sanitizer sobre ASTs arbitrarios (sin pasar por los límites del parser) -------


def clean_text(value: str) -> str:
    return "".join(char for char in value if not has_forbidden_text_chars(char))


def sanitized(*blocks: Block) -> Document:
    return sanitize(Document(blocks))


@given(nasty_text)
def test_sanitizer_removes_exactly_the_forbidden_characters_everywhere(value: str) -> None:
    cleaned = clean_text(value)
    text = (Text(cleaned),) if cleaned else ()
    assert sanitized(Paragraph((Text(value),))) == Document((Paragraph(text),))
    assert sanitized(Paragraph((InlineCode(value),))) == Document(
        (Paragraph((InlineCode(cleaned),)),)
    )
    assert sanitized(Paragraph((Image("/u", value),))) == Document(
        (Paragraph((Image("/u", cleaned),)),)
    )
    assert sanitized(CodeBlock(value)) == Document((CodeBlock(cleaned),))


language_values = st.one_of(
    st.none(), nasty_text, st.from_regex(r"[A-Za-z0-9_+-]{0,40}", fullmatch=True)
)


@pytest.mark.parametrize(("size", "kept"), [(1, True), (32, True), (33, False), (64, False)])
def test_sanitizer_language_length_boundary(size: int, kept: bool) -> None:
    language = "a" * size
    assert sanitized(CodeBlock("x", language)) == Document(
        (CodeBlock("x", language if kept else None),)
    )


@given(language_values)
def test_sanitizer_keeps_only_well_formed_languages(language: str | None) -> None:
    valid = language is not None and LANGUAGE_NAME.fullmatch(language) is not None
    assert sanitized(CodeBlock("x", language)) == Document(
        (CodeBlock("x", language if valid else None),)
    )


url_tails = st.lists(nasty_piece, max_size=12).map("".join)
any_url = st.one_of(
    st.builds("".join, st.tuples(st.sampled_from(SCHEMES), url_tails)),
    st.builds(lambda size: "/" + "a" * (size - 1), st.integers(2040, 2060)),
    url_tails,
)


@example("/a" + chr(0x200B))
@example("/a" + chr(0xAD) + "b")
@example("/a" + chr(0xA0) + "b")
@example("/a" + chr(0x202E))
@example("/a" + chr(0x7F))
@example("/a b")
@example("/a\\b")
@example("")
@example("/" + "a" * 2048)
@given(any_url)
def test_sanitizer_keeps_links_and_images_exactly_when_the_url_is_safe(url: str) -> None:
    link = sanitized(Paragraph((Link(url, (Text("t"),)),)))
    image = sanitized(Paragraph((Image(url, "t"),)))
    if url_is_safe(url):
        assert link == Document((Paragraph((Link(url, (Text("t"),)),)),))
        assert image == Document((Paragraph((Image(url, "t"),)),))
    else:
        assert link == Document((Paragraph((Text("t"),)),))
        assert image == Document((Paragraph((Text("t"),)),))


@example("#", "a:b")
@example("?", "a:b")
@example("HTTP://", "x")
@given(
    st.sampled_from(["http://", "https://", "mailto:", "HTTP://", "MailTo:", "//", "/", "#", "?"]),
    st.from_regex(r"[A-Za-z0-9._~:@/-]{1,20}", fullmatch=True),
)
def test_safe_urls_survive_the_whole_pipeline(prefix: str, rest: str) -> None:
    url = prefix + rest
    assert url_is_safe(url)
    link = f'<a href="{html.escape(url)}" rel="noopener noreferrer">t</a>'
    assert convert(f"[t]({url})") == f"<p>{link}</p>\n"
    assert convert(f"![t]({url})") == f'<p><img src="{html.escape(url)}" alt="t"></p>\n'


@given(
    st.from_regex(r"[a-z]{1,6}", fullmatch=True),
    st.from_regex(r"[a-z]{1,6}", fullmatch=True),
    st.from_regex(r"[a-z]{1,6}", fullmatch=True),
    st.sampled_from(["javascript:x", "data:x", "vbscript:x", "JAVASCRIPT:x"]),
)
def test_unsafe_urls_keep_their_text_in_place(a: str, b: str, c: str, bad: str) -> None:
    source = f"{a} **{b}** [{c}]({bad}) {a} ![{b}]({bad}) {c}"
    expected = f"<p>{a} <strong>{b}</strong> {c} {a} {b} {c}</p>\n"
    assert convert(source) == expected


@pytest.mark.parametrize(("size", "kept"), [(2047, True), (2048, True), (2049, False)])
def test_sanitizer_url_length_boundary(size: int, kept: bool) -> None:
    url = "/" + "a" * (size - 1)
    result = sanitized(Paragraph((Link(url, (Text("t"),)),)))
    expected = Link(url, (Text("t"),)) if kept else Text("t")
    assert result == Document((Paragraph((expected,)),))


def nested_inline(levels: int) -> Inline:
    node: Inline = Text("x")
    for _ in range(levels):
        node = Emphasis((node,))
    return node


def nested_blocks(levels: int) -> Block:
    node: Block = Paragraph((Text("x"),))
    for _ in range(levels):
        node = BlockQuote((node,))
    return node


@pytest.mark.parametrize("levels", [0, 1, 61, 62])
def test_sanitizer_accepts_nesting_just_below_the_limit(levels: int) -> None:
    inline_document = Document((Paragraph((nested_inline(levels),)),))
    block_document = Document((nested_blocks(levels),))
    assert sanitize(inline_document) == inline_document
    assert sanitize(block_document) == block_document


@pytest.mark.parametrize("levels", [63, 64, 100])
def test_sanitizer_rejects_nesting_at_the_limit(levels: int) -> None:
    inline_document = Document((Paragraph((nested_inline(levels),)),))
    with pytest.raises(SanitizationError):
        sanitize(inline_document)
    block_document = Document((nested_blocks(levels),))
    with pytest.raises(SanitizationError):
        sanitize(block_document)


# --- fortaleza: límites de recursos del inline, parser y lexer --------------------------------


@pytest.mark.parametrize("levels", [0, 1, 5, 31, 32, 33, 34, 40])
def test_inline_emphasis_depth_is_capped_exactly(levels: int) -> None:
    source = "*a " * levels + "b" + "*" * levels
    assert inline_depth(parse_inline(source)) == min(levels, 32)


@pytest.mark.parametrize("levels", [0, 1, 30, 31, 32, 33, 40])
def test_inline_link_depth_counts_towards_the_cap(levels: int) -> None:
    source = "[" + "*a " * levels + "b" + "*" * levels + "](/u)"
    assert inline_depth(parse_inline(source)) == min(levels + 1, 32)


def test_inline_delimiter_runs_are_capped() -> None:
    nodes = parse_inline("*a* " * 1500)
    assert sum(isinstance(node, Emphasis) for node in nodes) == 1000


def test_inline_open_brackets_are_capped() -> None:
    nodes = parse_inline("[" * 1200 + "x](/u)")
    link = nodes[-1]
    assert isinstance(link, Link)
    assert link.children == (Text("[" * 200 + "x"),)


@pytest.mark.parametrize(("size", "is_link"), [(2047, True), (2048, True), (2049, False)])
def test_inline_url_length_is_capped(size: int, is_link: bool) -> None:
    nodes = parse_inline("[a](/" + "u" * (size - 1) + ")")
    assert isinstance(nodes[0], Link) is is_link


@pytest.mark.parametrize("depth", [1, 7, 8])
def test_parser_accepts_quote_nesting_up_to_the_limit(depth: int) -> None:
    assert parse(tokenize("> " * depth + "x")).children


@pytest.mark.parametrize("depth", [9, 10, 30])
def test_parser_rejects_quote_nesting_over_the_limit(depth: int) -> None:
    tokens = tokenize("> " * depth + "x")
    with pytest.raises(ParserError):
        parse(tokens)


@pytest.mark.parametrize(
    "source",
    ["a" * 100_000, "\n" * 200_000, ("a" * 999 + "\n") * 2_000],
    ids=["line-at-limit", "lines-at-limit", "input-at-limit"],
)
def test_lexer_accepts_inputs_exactly_at_the_limits(source: str) -> None:
    assert tokenize(source)


@pytest.mark.parametrize(
    "source",
    ["a" * 100_001, "\n" * 200_001, ("a" * 999 + "\n") * 2_000 + "a"],
    ids=["line-over", "lines-over", "input-over"],
)
def test_lexer_rejects_inputs_one_past_the_limits(source: str) -> None:
    with pytest.raises(LexerError):
        tokenize(source)


@given(any_text)
def test_every_newline_convention_gives_the_same_html(text: str) -> None:
    normalized = re.sub(r"\r\n?", chr(10), text)
    try:
        expected = convert(normalized)
    except (LexerError, ParserError):
        return
    assert convert(text) == expected


@given(any_text)
def test_a_trailing_newline_does_not_add_tokens(text: str) -> None:
    assume(text and not text.endswith((chr(10), chr(13))))
    assert tokenize(text + chr(10)) == tokenize(text)
