import re
from collections.abc import Callable

import pytest

from markforge.errors import ParserError

URL_ATTR = re.compile(r"""\b(?:href|src)="([^"]*)\"""")
QUOTED_VALUE = re.compile(r'"[^"]*"')
TAG_WITH_EVENT = re.compile(r"<[^>]*\son\w+\s*=", re.IGNORECASE)
FORBIDDEN_SCHEMES = ("javascript:", "data:", "vbscript:")

PAYLOADS = [
    "<script>alert(1)</script>",
    "<SCRIPT SRC=//evil.example/x.js></SCRIPT>",
    "<img src=x onerror=alert(1)>",
    "<svg/onload=alert(1)>",
    "<iframe src=javascript:alert(1)></iframe>",
    "**<b onclick=alert(1)>x</b>**",
    "> <script>alert(1)</script>",
    "- <script>alert(1)</script>",
    "# <script>alert(1)</script>",
    "[x](javascript:alert(1))",
    "[x](JaVaScRiPt:alert(1))",
    "[x](  javascript:alert(1))",
    "[x](vbscript:msgbox(1))",
    "[x](data:text/html,<script>alert(1)</script>)",
    "[x](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==)",
    "![x](javascript:alert(1))",
    "![x](data:image/svg+xml;base64,AAAA)",
    '[x](https://a.b/"onmouseover="alert(1))',
    '![x](https://a.b/i.png"onerror="alert(1))',
    '![a" onerror="alert(1)](https://a.b/i.png)',
    "[z](&#106;avascript:alert(1))",
    "[z](&#x6A;avascript:alert(1))",
    "[z](java" + chr(9) + "script:alert(1))",
    "[z](java" + chr(10) + "script:alert(1))",
    "[z](" + chr(0x200B) + "javascript:alert(1))",
    "[z](" + chr(0x202E) + "javascript:alert(1))",
    '```"onmouseover=alert(1)\n<script>x</script>\n```',
    "```><script>alert(1)</script>\nx\n```",
    "`<script>alert(1)</script>`",
    "[<script>alert(1)</script>](https://a.b)",
    "[**[x](javascript:alert(1))**](https://a.b)",
    "> - [x](javascript:alert(1))",
]


def assert_no_executable_html(output: str) -> None:
    assert "<script" not in output.lower()
    without_values = QUOTED_VALUE.sub('""', output)
    assert TAG_WITH_EVENT.search(without_values) is None
    for url in URL_ATTR.findall(output):
        assert not url.strip().lower().startswith(FORBIDDEN_SCHEMES)


@pytest.mark.parametrize("payload", PAYLOADS)
def test_payload_produces_no_executable_html(payload: str, convert: Callable[[str], str]) -> None:
    assert_no_executable_html(convert(payload))


@pytest.mark.parametrize("payload", PAYLOADS)
def test_payload_only_emits_known_tags(payload: str, convert: Callable[[str], str]) -> None:
    allowed = {"p", "h1", "blockquote", "ul", "li", "pre", "code", "a", "img", "strong", "em"}
    names = {
        m.group(1).lower() for m in re.finditer(r"</?([a-zA-Z][a-zA-Z0-9]*)", convert(payload))
    }
    assert names <= allowed


def test_script_tag_text_is_escaped_not_dropped(convert: Callable[[str], str]) -> None:
    output = convert("<script>alert(1)</script>")
    assert output == "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>\n"


def test_javascript_link_keeps_only_its_text(convert: Callable[[str], str]) -> None:
    output = convert("[clic](javascript:alert)")
    assert output == "<p>clic</p>\n"


def test_javascript_image_keeps_only_its_alt(convert: Callable[[str], str]) -> None:
    output = convert("![mi alt](javascript:alert)")
    assert output == "<p>mi alt</p>\n"


def test_quote_breakout_stays_inside_the_attribute(convert: Callable[[str], str]) -> None:
    output = convert('[q](https://a.b/"onmouseover="alert(1))')
    assert '"onmouseover=' not in output
    assert "&quot;onmouseover=&quot;" in output


def test_malicious_fence_language_is_dropped(convert: Callable[[str], str]) -> None:
    output = convert('```"onmouseover=alert(1)\nx\n```')
    assert output == "<pre><code>x\n</code></pre>\n"


def test_safe_links_still_work(convert: Callable[[str], str]) -> None:
    output = convert("[a](https://a.b/x) ![i](/img.png)")
    assert 'href="https://a.b/x" rel="noopener noreferrer"' in output
    assert 'src="/img.png"' in output


def test_every_link_gets_rel_noopener_noreferrer(convert: Callable[[str], str]) -> None:
    output = convert("[a](https://a.b) [b](mailto:a@b.c) [c](/x)")
    assert output.count("<a ") == output.count('rel="noopener noreferrer"')


def test_deeply_nested_payload_does_not_escape(convert: Callable[[str], str]) -> None:
    source = ">" * 6 + " <script>alert(1)</script>"
    assert_no_executable_html(convert(source))


def test_too_deep_quote_nesting_is_rejected_not_rendered(
    convert: Callable[[str], str],
) -> None:
    with pytest.raises(ParserError, match="cita anidada"):
        convert(">" * 40 + " <script>alert(1)</script>")
