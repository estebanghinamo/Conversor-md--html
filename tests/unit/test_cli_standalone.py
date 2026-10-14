from pathlib import Path

import pytest

from markforge.cli import EXIT_INVALID_INPUT, EXIT_OK, main


@pytest.fixture
def source(tmp_path: Path) -> Path:
    path = tmp_path / "in.md"
    path.write_bytes(b"# Hola\n\n[x](javascript:alert) <script>1</script>\n")
    return path


def test_standalone_wraps_output(source: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(source), "--standalone"]) == EXIT_OK
    out = capsys.readouterr().out
    assert out.startswith("<!doctype html>")
    assert "<h1>Hola</h1>" in out
    assert "<title>MarkForge</title>" in out


def test_standalone_keeps_sanitizing(source: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main([str(source), "--standalone"])
    out = capsys.readouterr().out
    body = out.split("<body>")[1]
    assert 'href="javascript' not in body
    assert "<script>" not in body


def test_custom_title_is_escaped(source: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main([str(source), "--standalone", "--title", "<b>x</b>"])
    assert "<title>&lt;b&gt;x&lt;/b&gt;</title>" in capsys.readouterr().out


def test_without_flag_output_is_a_fragment(
    source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main([str(source)])
    out = capsys.readouterr().out
    assert "<!doctype" not in out
    assert out.startswith("<h1>Hola</h1>")


def test_invalid_utf8_title_is_a_controlled_error(
    source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    surrogate = chr(0xDCFF)
    assert main([str(source), "--standalone", "--title", surrogate]) == EXIT_INVALID_INPUT
    captured = capsys.readouterr()
    assert "--title no es UTF-8" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_standalone_to_output_file(source: Path, tmp_path: Path) -> None:
    target = tmp_path / "out.html"
    assert main([str(source), "--standalone", "-o", str(target)]) == EXIT_OK
    assert target.read_text(encoding="utf-8").startswith("<!doctype html>")
