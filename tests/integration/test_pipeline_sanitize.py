from markforge.ast import CodeBlock, Document, Image, Link, Paragraph, Text
from markforge.lexer import tokenize
from markforge.parser import parse
from markforge.sanitizer import sanitize


def run(source: str) -> Document:
    return sanitize(parse(tokenize(source)))


def walk(node: object) -> list[object]:
    found = [node]
    for attr in ("children", "items"):
        for child in getattr(node, attr, ()):
            found.extend(walk(child))
    return found


def urls(document: Document) -> list[str]:
    return [n.url for n in walk(document) if isinstance(n, (Link, Image))]


def test_javascript_link_is_replaced_by_its_text() -> None:
    document = run("[clic](javascript:alert)")
    assert document == Document((Paragraph((Text("clic"),)),))


def test_mixed_case_javascript_link_is_blocked() -> None:
    assert urls(run("[x](JaVaScRiPt:alert(1))")) == []


def test_data_link_is_blocked() -> None:
    assert urls(run("[x](data:text/html,<script>alert(1)</script>)")) == []


def test_vbscript_link_is_blocked() -> None:
    assert urls(run("[x](vbscript:msgbox(1))")) == []


def test_javascript_image_becomes_alt_text() -> None:
    document = run("![mi alt](javascript:alert)")
    assert document == Document((Paragraph((Text("mi alt"),)),))


def test_data_image_is_blocked() -> None:
    assert urls(run("![x](data:image/svg+xml;base64,AAAA)")) == []


def test_safe_urls_survive_the_pipeline() -> None:
    document = run("[a](https://a.b/x) ![i](/img.png) [m](mailto:a@b.c)")
    assert urls(document) == ["https://a.b/x", "/img.png", "mailto:a@b.c"]


def test_blocked_link_nested_in_emphasis_and_list_and_quote() -> None:
    source = "> - **[x](javascript:a)** y\n"
    assert urls(run(source)) == []


def test_malicious_language_is_dropped() -> None:
    document = run('```"onmouseover=alert(1) x\ncode\n```')
    blocks = [n for n in walk(document) if isinstance(n, CodeBlock)]
    assert blocks
    assert all(block.language is None for block in blocks)


def test_valid_language_survives_the_pipeline() -> None:
    document = run("```python\nprint(1)\n```")
    blocks = [n for n in walk(document) if isinstance(n, CodeBlock)]
    assert [block.language for block in blocks] == ["python"]


def test_raw_html_text_is_not_escaped_before_renderer() -> None:
    document = run("<script>alert(1)</script>")
    texts = [n.value for n in walk(document) if isinstance(n, Text)]
    assert "".join(texts) == "<script>alert(1)</script>"
