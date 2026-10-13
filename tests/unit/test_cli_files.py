import os
from pathlib import Path

import pytest

from markforge.cli import EXIT_IO_ERROR, EXIT_OK, main

NUL = chr(0)


@pytest.fixture
def source(tmp_path: Path) -> Path:
    path = tmp_path / "in.md"
    path.write_bytes(b"hola\n")
    return path


def test_hard_link_to_the_input_is_refused_and_input_is_kept(
    source: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    link = tmp_path / "hard.md"
    try:
        os.link(source, link)
    except OSError:
        pytest.skip("el sistema de archivos no permite hard links")
    assert main([str(source), "-o", str(link)]) == EXIT_IO_ERROR
    assert "mismo archivo" in capsys.readouterr().err
    assert source.read_bytes() == b"hola\n"


def test_symlink_to_the_input_is_refused_and_input_is_kept(source: Path, tmp_path: Path) -> None:
    link = tmp_path / "sym.md"
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("no hay permiso para crear symlinks")
    assert main([str(source), "-o", str(link)]) == EXIT_IO_ERROR
    assert source.read_bytes() == b"hola\n"


def test_existing_different_output_file_is_overwritten(source: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.html"
    out.write_text("viejo")
    assert main([str(source), "-o", str(out)]) == EXIT_OK
    assert out.read_bytes() == b"<p>hola</p>\n"


def test_nul_in_input_path_is_io_error_not_a_traceback(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["a" + NUL + "b"]) == EXIT_IO_ERROR
    err = capsys.readouterr().err
    assert "no se pudo leer" in err
    assert "Traceback" not in err


def test_nul_in_output_path_is_io_error_not_a_traceback(
    source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(source), "-o", "a" + NUL + "b"]) == EXIT_IO_ERROR
    err = capsys.readouterr().err
    assert "no se pudo escribir" in err
    assert "Traceback" not in err
