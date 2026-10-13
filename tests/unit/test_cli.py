import io
import runpy
import sys
from pathlib import Path

import pytest

from markforge import __version__, cli
from markforge.cli import EXIT_INVALID_INPUT, EXIT_IO_ERROR, EXIT_OK, main
from markforge.lexer import MAX_INPUT_LENGTH


class FakeStdin(io.TextIOWrapper):
    """Stdin de prueba con `.buffer` binario y `isatty` configurable."""

    def __init__(self, data: bytes, *, tty: bool = False) -> None:
        super().__init__(io.BytesIO(data))
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def set_stdin(monkeypatch: pytest.MonkeyPatch, data: bytes, *, tty: bool = False) -> None:
    monkeypatch.setattr(sys, "stdin", FakeStdin(data, tty=tty))


@pytest.fixture
def source(tmp_path: Path) -> Path:
    path = tmp_path / "in.md"
    path.write_bytes(b"# Hola\n\ntexto **fuerte**\n")
    return path


HTML = "<h1>Hola</h1>\n<p>texto <strong>fuerte</strong></p>\n"


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert f"markforge {__version__}" in capsys.readouterr().out


def test_help_shows_usage(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--output" in out
    assert "códigos de salida" in out


def test_file_to_stdout(source: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(source)]) == EXIT_OK
    captured = capsys.readouterr()
    assert captured.out == HTML
    assert captured.err == ""


def test_file_to_output_file(source: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.html"
    assert main([str(source), "--output", str(out)]) == EXIT_OK
    assert out.read_bytes() == HTML.encode()


def test_output_short_flag(source: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.html"
    assert main([str(source), "-o", str(out)]) == EXIT_OK
    assert out.exists()


def test_output_file_is_overwritten(source: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.html"
    out.write_text("viejo")
    assert main([str(source), "-o", str(out)]) == EXIT_OK
    assert out.read_bytes() == HTML.encode()


def test_stdin_without_argument(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_stdin(monkeypatch, b"# Hola\n\ntexto **fuerte**\n")
    assert main([]) == EXIT_OK
    assert capsys.readouterr().out == HTML


def test_stdin_with_dash(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_stdin(monkeypatch, b"*a*")
    assert main(["-"]) == EXIT_OK
    assert capsys.readouterr().out == "<p><em>a</em></p>\n"


def test_stdin_to_output_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    set_stdin(monkeypatch, b"*a*")
    out = tmp_path / "out.html"
    assert main(["-", "-o", str(out)]) == EXIT_OK
    assert out.read_bytes() == b"<p><em>a</em></p>\n"


def test_empty_input_gives_empty_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_stdin(monkeypatch, b"")
    assert main([]) == EXIT_OK
    assert capsys.readouterr().out == ""


def test_no_input_on_a_terminal_is_a_usage_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_stdin(monkeypatch, b"", tty=True)
    assert main([]) == EXIT_IO_ERROR
    assert "falta el archivo de entrada" in capsys.readouterr().err


def test_utf8_output_is_not_mangled(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_stdin(monkeypatch, "ñandú ✓ 日本".encode())
    assert main([]) == EXIT_OK
    assert capsys.readouterr().out == "<p>ñandú ✓ 日本</p>\n"


def test_utf8_bom_is_ignored(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_stdin(monkeypatch, b"\xef\xbb\xbf# T")
    assert main([]) == EXIT_OK
    assert capsys.readouterr().out == "<h1>T</h1>\n"


def test_invalid_utf8_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_stdin(monkeypatch, b"\xff\xfe\xfa")
    assert main([]) == EXIT_INVALID_INPUT
    captured = capsys.readouterr()
    assert "UTF-8" in captured.err
    assert captured.out == ""


def test_input_over_byte_limit_is_rejected_before_decoding(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "MAX_INPUT_BYTES", 10)
    set_stdin(monkeypatch, b"a" * 11)
    assert main([]) == EXIT_INVALID_INPUT
    assert "tamaño máximo" in capsys.readouterr().err


def test_input_at_byte_limit_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "MAX_INPUT_BYTES", 10)
    set_stdin(monkeypatch, b"a" * 10)
    assert main([]) == EXIT_OK


def test_byte_limit_covers_the_lexer_limit() -> None:
    assert cli.MAX_INPUT_BYTES >= MAX_INPUT_LENGTH


def test_lexer_limit_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_stdin(monkeypatch, b"a" * (MAX_INPUT_LENGTH + 1))
    assert main([]) == EXIT_INVALID_INPUT
    err = capsys.readouterr().err
    assert err.startswith("markforge: error:")
    assert "excede" in err


def test_too_deep_blockquote_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_stdin(monkeypatch, b">" * 50 + b" x")
    assert main([]) == EXIT_INVALID_INPUT
    assert "anidada" in capsys.readouterr().err


def test_missing_file_is_io_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "no-existe.md"
    assert main([str(missing)]) == EXIT_IO_ERROR
    err = capsys.readouterr().err
    assert "no se pudo leer" in err
    assert "Traceback" not in err


def test_directory_as_input_is_io_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path)]) == EXIT_IO_ERROR
    assert "no se pudo leer" in capsys.readouterr().err


def test_stdin_read_failure_is_io_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Broken(FakeStdin):
        @property
        def buffer(self) -> io.BufferedIOBase:  # type: ignore[override]
            raise OSError("fallo")

    monkeypatch.setattr(sys, "stdin", Broken(b""))
    assert main([]) == EXIT_IO_ERROR
    assert "stdin" in capsys.readouterr().err


def test_output_in_missing_directory_is_io_error(
    source: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "no-existe" / "out.html"
    assert main([str(source), "-o", str(out)]) == EXIT_IO_ERROR
    assert "no se pudo escribir" in capsys.readouterr().err


def test_output_equal_to_input_is_refused_and_input_is_kept(
    source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    original = source.read_bytes()
    assert main([str(source), "-o", str(source)]) == EXIT_IO_ERROR
    assert "mismo archivo" in capsys.readouterr().err
    assert source.read_bytes() == original


def test_output_equal_to_input_through_another_path_is_refused(
    source: Path, tmp_path: Path
) -> None:
    alias = tmp_path / "." / "in.md"
    original = source.read_bytes()
    assert main([str(source), "-o", str(alias)]) == EXIT_IO_ERROR
    assert source.read_bytes() == original


def test_failed_conversion_does_not_touch_the_output_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out = tmp_path / "out.html"
    out.write_text("previo")
    set_stdin(monkeypatch, b">" * 50)
    assert main(["-", "-o", str(out)]) == EXIT_INVALID_INPUT
    assert out.read_text() == "previo"


def test_stdout_write_failure_is_io_error(
    source: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class BrokenPipe(io.TextIOWrapper):
        @property
        def buffer(self) -> io.BufferedIOBase:  # type: ignore[override]
            raise BrokenPipeError

    monkeypatch.setattr(sys, "stdout", BrokenPipe(io.BytesIO()))
    assert main([str(source)]) == EXIT_IO_ERROR
    assert "stdout" in capsys.readouterr().err


def test_stdout_without_binary_buffer_falls_back_to_text(
    source: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    text_only = io.StringIO()
    monkeypatch.setattr(sys, "stdout", text_only)
    assert main([str(source)]) == EXIT_OK
    assert text_only.getvalue() == HTML


def test_error_messages_do_not_include_input_content(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    marker = "contenido-privado-del-usuario"
    set_stdin(monkeypatch, (">" * 50 + " " + marker).encode())
    assert main([]) == EXIT_INVALID_INPUT
    assert marker not in capsys.readouterr().err


def test_dangerous_markdown_is_neutralized_end_to_end(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_stdin(monkeypatch, b"[x](javascript:alert) <script>alert(1)</script>")
    assert main([]) == EXIT_OK
    out = capsys.readouterr().out
    assert "<script" not in out
    assert "javascript:" not in out
    assert "href" not in out


def test_python_dash_m_entry_point(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["markforge", "--version"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("markforge", run_name="__main__")
    assert exc.value.code == 0
    assert f"markforge {__version__}" in capsys.readouterr().out


def test_unknown_option_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--no-existe"])
    assert exc.value.code == EXIT_IO_ERROR
    assert "usage" in capsys.readouterr().err


def test_output_flag_without_value_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["-o"])
    assert exc.value.code == EXIT_IO_ERROR
    assert "expected one argument" in capsys.readouterr().err


def test_invalid_utf8_file_is_invalid_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"ok \xff\xfe")
    assert main([str(bad)]) == EXIT_INVALID_INPUT
    captured = capsys.readouterr()
    assert "UTF-8" in captured.err
    assert captured.out == ""


def test_oversized_file_is_invalid_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "MAX_INPUT_BYTES", 10)
    big = tmp_path / "big.md"
    big.write_bytes(b"a" * 11)
    assert main([str(big)]) == EXIT_INVALID_INPUT
    assert "tamaño máximo" in capsys.readouterr().err


def _document_of_length(char: str, length: int) -> str:
    line = char * 99 + "\n"
    return (line * (length // len(line) + 1))[:length]


def test_multibyte_input_within_char_limit_is_not_rejected_by_byte_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _document_of_length("ñ", MAX_INPUT_LENGTH)
    assert len(text.encode()) > MAX_INPUT_LENGTH
    set_stdin(monkeypatch, text.encode())
    assert main([]) == EXIT_OK


def test_input_at_char_limit_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    set_stdin(monkeypatch, _document_of_length("a", MAX_INPUT_LENGTH).encode())
    assert main([]) == EXIT_OK


def test_crlf_input_is_normalized(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_stdin(monkeypatch, b"# T\r\n\r\ntexto\r\n")
    assert main([]) == EXIT_OK
    assert capsys.readouterr().out == "<h1>T</h1>\n<p>texto</p>\n"


def test_bom_only_input_gives_empty_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_stdin(monkeypatch, b"\xef\xbb\xbf")
    assert main([]) == EXIT_OK
    assert capsys.readouterr().out == ""


def test_stdin_with_dash_and_output_equal_to_a_file_named_like_input_is_allowed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out = tmp_path / "in.md"
    out.write_text("previo")
    set_stdin(monkeypatch, b"*a*")
    assert main(["-", "-o", str(out)]) == EXIT_OK
    assert out.read_bytes() == b"<p><em>a</em></p>\n"


def test_output_path_is_a_directory_is_io_error(
    source: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(source), "-o", str(tmp_path)]) == EXIT_IO_ERROR
    err = capsys.readouterr().err
    assert "no se pudo escribir" in err
    assert "Traceback" not in err


def test_output_to_file_leaves_stdout_empty(
    source: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(source), "-o", str(tmp_path / "o.html")]) == EXIT_OK
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_stdout_text_fallback_write_failure_is_io_error(
    source: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class FullDisk(io.StringIO):
        def write(self, _text: str) -> int:
            raise OSError(28, "No space left on device")

    monkeypatch.setattr(sys, "stdout", FullDisk())
    assert main([str(source)]) == EXIT_IO_ERROR
    assert "No space left" in capsys.readouterr().err


def test_exit_codes_are_distinct_and_stable() -> None:
    assert (EXIT_OK, EXIT_INVALID_INPUT, EXIT_IO_ERROR) == (0, 1, 2)
