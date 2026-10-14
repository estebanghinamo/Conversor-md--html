from markforge.page import DEFAULT_TITLE, wrap_page


def test_wraps_fragment_in_full_document() -> None:
    page = wrap_page("<p>hola</p>\n")
    assert page.startswith("<!doctype html>\n")
    assert '<meta charset="utf-8">' in page
    assert "<body>\n<p>hola</p>\n</body>" in page
    assert page.endswith("</html>\n")


def test_default_title() -> None:
    assert f"<title>{DEFAULT_TITLE}</title>" in wrap_page("")


def test_title_is_escaped() -> None:
    page = wrap_page("", "</title><script>alert(1)</script>")
    assert "<title>&lt;/title&gt;&lt;script&gt;alert(1)&lt;/script&gt;</title>" in page
    assert "<script" not in page


def test_page_has_restrictive_csp_and_no_scripts() -> None:
    page = wrap_page("<p>x</p>\n")
    assert "default-src 'none'" in page
    assert "base-uri 'none'" in page
    assert "form-action 'none'" in page
    assert "script-src" not in page
    assert "<script" not in page


def test_fragment_is_inserted_verbatim() -> None:
    fragment = "<p>a &lt;b&gt;</p>\n"
    assert fragment in wrap_page(fragment)
