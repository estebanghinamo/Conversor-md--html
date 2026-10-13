from collections.abc import Callable
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
MARKDOWN_DIR = FIXTURES / "markdown"
EXPECTED_DIR = FIXTURES / "expected_html"
CASES = sorted(MARKDOWN_DIR.glob("*.md"))


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def test_every_markdown_fixture_has_an_expected_html() -> None:
    expected = sorted(path.stem for path in EXPECTED_DIR.glob("*.html"))
    assert [path.stem for path in CASES] == expected


def test_golden_fixtures_are_present() -> None:
    assert len(CASES) >= 10


@pytest.mark.parametrize("markdown", CASES, ids=lambda path: path.stem)
def test_golden(markdown: Path, convert: Callable[[str], str]) -> None:
    expected = read(EXPECTED_DIR / f"{markdown.stem}.html")
    assert convert(read(markdown)) == expected
