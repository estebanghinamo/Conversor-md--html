import time

import pytest

from markforge.ast import (
    Emphasis,
    Image,
    Inline,
    InlineCode,
    Link,
    Strikethrough,
    Strong,
    Text,
)
from markforge.inline import (
    MAX_DELIMITER_RUNS,
    MAX_INLINE_DEPTH,
    MAX_OPEN_BRACKETS,
    MAX_URL_LENGTH,
    parse_inline,
)


def t(value: str) -> Text:
    return Text(value)


def depth(nodes: tuple[Inline, ...]) -> int:
    levels = 0
    for node in nodes:
        if isinstance(node, Emphasis | Strong | Strikethrough | Link):
            levels = max(levels, 1 + depth(node.children))
    return levels


def test_empty_and_plain_text() -> None:
    assert parse_inline("") == ()
    assert parse_inline("hola mundo") == (t("hola mundo"),)


def test_emphasis_and_strong() -> None:
    assert parse_inline("*a*") == (Emphasis((t("a"),)),)
    assert parse_inline("**a**") == (Strong((t("a"),)),)
    assert parse_inline("x *a* y") == (t("x "), Emphasis((t("a"),)), t(" y"))


def test_triple_delimiters_nest_strong_in_emphasis() -> None:
    assert parse_inline("***a***") == (Emphasis((Strong((t("a"),)),)),)


def test_nested_emphasis_and_strong() -> None:
    assert parse_inline("**a *b* c**") == (Strong((t("a "), Emphasis((t("b"),)), t(" c"))),)


def test_strikethrough() -> None:
    assert parse_inline("~~a~~") == (Strikethrough((t("a"),)),)


@pytest.mark.parametrize("source", ["~a~", "~~~a~~~", "a ~~ b", "~~a"])
def test_invalid_strikethrough_is_text(source: str) -> None:
    assert parse_inline(source) == (t(source),)


@pytest.mark.parametrize("source", ["a * b", "**", "*a", "a**", "* a *", "2 * 3 * 4"])
def test_unmatched_or_spaced_delimiters_are_text(source: str) -> None:
    assert parse_inline(source) == (t(source),)


def test_intraword_emphasis() -> None:
    assert parse_inline("a*b*c") == (t("a"), Emphasis((t("b"),)), t("c"))


def test_underscore_is_plain_text() -> None:
    assert parse_inline("snake_case_name _a_") == (t("snake_case_name _a_"),)


def test_inline_code() -> None:
    assert parse_inline("`a`") == (InlineCode("a"),)
    assert parse_inline("x `a *b*` y") == (t("x "), InlineCode("a *b*"), t(" y"))


def test_inline_code_with_longer_fence_and_padding() -> None:
    assert parse_inline("`` a`b ``") == (InlineCode("a`b"),)
    assert parse_inline("`  `") == (InlineCode("  "),)


def test_inline_code_converts_newlines_to_spaces() -> None:
    assert parse_inline("`a" + chr(10) + "b`") == (InlineCode("a b"),)


def test_unclosed_code_is_text() -> None:
    assert parse_inline("`a") == (t("`a"),)
    assert parse_inline("``a`") == (t("``a`"),)


def test_link() -> None:
    assert parse_inline("[x](http://a.b)") == (Link("http://a.b", (t("x"),)),)


def test_link_with_inline_children() -> None:
    assert parse_inline("[*x* `y`](u)") == (
        Link("u", (Emphasis((t("x"),)), t(" "), InlineCode("y"))),
    )


def test_two_links_in_text() -> None:
    assert parse_inline("[a](u) y [b](v)") == (
        Link("u", (t("a"),)),
        t(" y "),
        Link("v", (t("b"),)),
    )


def test_image() -> None:
    assert parse_inline("![alt](http://a.b/i.png)") == (Image("http://a.b/i.png", "alt"),)


def test_image_alt_is_plain_text() -> None:
    assert parse_inline("![a *b* `c`](u)") == (Image("u", "a b c"),)


def test_image_alt_flattens_nested_image() -> None:
    assert parse_inline("![a ![b](i)](u)") == (Image("u", "a b"),)


def test_unresolved_delimiter_inside_link_text_stays_literal() -> None:
    assert parse_inline("*a [b *c](u) d*") == (
        Emphasis((t("a "), Link("u", (t("b *c"),)), t(" d"))),
    )


def test_different_delimiter_chars_do_not_match_each_other() -> None:
    assert parse_inline("*a ~~b* c~~") == (Emphasis((t("a ~~b"),)), t(" c~~"))


def test_image_inside_link() -> None:
    assert parse_inline("[![alt](i)](u)") == (Link("u", (Image("i", "alt"),)),)


@pytest.mark.parametrize(
    "source",
    ["[a]", "[a] (u)", "[a](", "[a]()", "[a](u v)", "]", "[", "![a]", "![a](", "!", "a ! b"],
)
def test_incomplete_links_and_images_are_text(source: str) -> None:
    assert parse_inline(source) == (t(source),)


def test_links_do_not_nest() -> None:
    assert parse_inline("[[a](u)](v)") == (t("["), Link("u", (t("a"),)), t("](v)"))


def test_emphasis_cannot_cross_link_boundary() -> None:
    assert parse_inline("*[a*](u)") == (t("*"), Link("u", (t("a*"),)))


def test_javascript_url_is_kept_raw_for_the_sanitizer() -> None:
    assert parse_inline("[x](javascript:alert(1))") == (
        Link("javascript:alert(1", (t("x"),)),
        t(")"),
    )


def test_html_is_not_interpreted() -> None:
    assert parse_inline("<b>x</b> & <script>") == (t("<b>x</b> & <script>"),)


def test_backslash_escapes() -> None:
    assert parse_inline("\\*a\\*") == (t("*a*"),)
    assert parse_inline("\\[a](u)") == (t("[a](u)"),)
    assert parse_inline("\\`a\\`") == (t("`a`"),)


def test_backslash_before_normal_char_or_end_is_literal() -> None:
    assert parse_inline("a\\b") == (t("a\\b"),)
    assert parse_inline("a\\") == (t("a\\"),)


def test_escaped_backslash() -> None:
    assert parse_inline("\\\\*a*") == (t("\\"), Emphasis((t("a"),)))


def test_delimiters_over_cap_are_text() -> None:
    source = "*a " * (MAX_DELIMITER_RUNS + 500)
    result = parse_inline(source)
    assert result == (t(source),)


def test_nesting_depth_is_bounded() -> None:
    count = MAX_INLINE_DEPTH + 10
    source = "*a " * count + "b*" + " a*" * (count - 1)
    assert depth(parse_inline(source)) <= MAX_INLINE_DEPTH


def test_nesting_below_limit_is_kept() -> None:
    source = "*a " * 5 + "b*" + " a*" * 4
    assert depth(parse_inline(source)) == 5


def test_link_nesting_depth_is_bounded() -> None:
    count = MAX_INLINE_DEPTH + 5
    source = "*a " * count + "[x](u)" + " a*" * count
    assert depth(parse_inline(source)) <= MAX_INLINE_DEPTH


def test_link_text_over_depth_limit_is_text() -> None:
    inner = "*a " * MAX_INLINE_DEPTH + "b*" + " a*" * (MAX_INLINE_DEPTH - 1)
    assert depth(parse_inline("[" + inner + "](u)")) <= MAX_INLINE_DEPTH


def test_open_brackets_over_cap_are_text() -> None:
    source = "[" * (MAX_OPEN_BRACKETS + 10)
    assert parse_inline(source) == (t(source),)


def test_url_longer_than_limit_is_not_a_link() -> None:
    source = "[a](" + "u" * (MAX_URL_LENGTH + 10) + ")"
    assert parse_inline(source) == (t(source),)


PATHOLOGICAL = {
    "openers": "*a " * 100_000,
    "closers": "a* " * 100_000,
    "strong_openers": "**a " * 50_000,
    "tilde_openers": "~~a " * 50_000,
    "open_brackets": "[" * 100_000,
    "close_brackets": "]" * 100_000,
    "open_images": "![" * 50_000,
    "empty_destinations": "[](" * 50_000,
    "unclosed_destinations": "[a](b" * 50_000,
    "code_runs": "`a``b```c" * 20_000,
    "backticks": "`" * 100_000,
    "backslashes": "\\" * 100_000,
    "mixed": "*[" * 50_000 + "](x)" * 50_000,
}


@pytest.mark.parametrize("name", list(PATHOLOGICAL))
def test_pathological_inputs_terminate(name: str) -> None:
    assert parse_inline(PATHOLOGICAL[name])


def test_depth_failures_do_not_cause_quadratic_time() -> None:
    source = "*a " * 33 + "x*" * 32 + "`x` " * 10_000 + " a*" * 1_900
    started = time.perf_counter()
    result = parse_inline(source)
    assert time.perf_counter() - started < 10
    assert depth(result) <= MAX_INLINE_DEPTH


def test_links_stop_after_depth_limit_is_exceeded() -> None:
    count = MAX_INLINE_DEPTH + 5
    source = "*a " * count + "[x](u)" + " a*" * count + " [y](v) ![i](w)"
    result = parse_inline(source)
    assert depth(result) <= MAX_INLINE_DEPTH
    assert not any(isinstance(node, Link | Image) for node in result[-1:])
