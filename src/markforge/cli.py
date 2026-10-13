"""Interfaz de línea de comandos (solo E/S).

Lee Markdown de un archivo o de stdin, llama a `convert` y escribe el HTML en
stdout o en un archivo. No contiene lógica de conversión.

Códigos de salida: 0 éxito, 1 input inválido (error de MarkForge, UTF-8 inválido
o demasiado grande), 2 error de E/S o de uso.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import BinaryIO

from markforge import convert
from markforge.errors import MarkdownError
from markforge.lexer import MAX_INPUT_LENGTH
from markforge.version import __version__

EXIT_OK = 0
EXIT_INVALID_INPUT = 1
EXIT_IO_ERROR = 2

# UTF-8 usa hasta 4 bytes por carácter: se acota la lectura antes de decodificar.
MAX_INPUT_BYTES = MAX_INPUT_LENGTH * 4

STDIN_NAME = "-"


class _CliError(Exception):
    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markforge",
        description="Convierte un subconjunto de Markdown a HTML seguro.",
        epilog=(
            "códigos de salida:\n"
            "  0  éxito\n"
            "  1  input inválido (error de MarkForge, UTF-8 inválido o demasiado grande)\n"
            "  2  error de E/S o de uso"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        nargs="?",
        help=f"archivo Markdown de entrada; sin argumento o con '{STDIN_NAME}' se lee stdin",
    )
    parser.add_argument("-o", "--output", help="archivo HTML de salida (por defecto, stdout)")
    parser.add_argument("--version", action="version", version=f"markforge {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source = _read_input(args.input)
        html = convert(source)
        _write_output(html, args.output, args.input)
    except _CliError as exc:
        print(f"markforge: error: {exc}", file=sys.stderr)
        return exc.code
    except MarkdownError as exc:
        print(f"markforge: error: {exc}", file=sys.stderr)
        return EXIT_INVALID_INPUT
    return EXIT_OK


def _io_message(action: str, name: str, exc: OSError | ValueError) -> str:
    reason = exc.strerror if isinstance(exc, OSError) else None
    return f"no se pudo {action} {name}: {reason or type(exc).__name__}"


def _read_input(path: str | None) -> str:
    if path is None and sys.stdin.isatty():
        msg = "falta el archivo de entrada (o pasar el Markdown por stdin)"
        raise _CliError(msg, EXIT_IO_ERROR)
    try:
        if path is None or path == STDIN_NAME:
            data = _read_limited(sys.stdin.buffer)
        else:
            with Path(path).open("rb") as stream:
                data = _read_limited(stream)
    except (OSError, ValueError) as exc:
        name = "stdin" if path is None or path == STDIN_NAME else f"'{path}'"
        raise _CliError(_io_message("leer", name, exc), EXIT_IO_ERROR) from exc
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        msg = "el input no es UTF-8 válido"
        raise _CliError(msg, EXIT_INVALID_INPUT) from exc


def _read_limited(stream: BinaryIO) -> bytes:
    data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        msg = "el input excede el tamaño máximo permitido"
        raise _CliError(msg, EXIT_INVALID_INPUT)
    return data


def _write_output(html: str, output: str | None, input_path: str | None) -> None:
    data = html.encode("utf-8")
    if output is None:
        _write_stdout(html, data)
        return
    try:
        if input_path not in (None, STDIN_NAME) and _same_file(output, str(input_path)):
            msg = "la salida no puede ser el mismo archivo que la entrada"
            raise _CliError(msg, EXIT_IO_ERROR)
        Path(output).write_bytes(data)
    except (OSError, ValueError) as exc:
        raise _CliError(_io_message("escribir", f"'{output}'", exc), EXIT_IO_ERROR) from exc


def _write_stdout(html: str, data: bytes) -> None:
    try:
        buffer = getattr(sys.stdout, "buffer", None)
        if buffer is None:
            sys.stdout.write(html)
            sys.stdout.flush()
        else:
            buffer.write(data)
            buffer.flush()
    except OSError as exc:
        raise _CliError(_io_message("escribir", "stdout", exc), EXIT_IO_ERROR) from exc


def _same_file(first: str, second: str) -> bool:
    """True si ambas rutas apuntan al mismo archivo (symlinks y hard links incluidos)."""
    left, right = Path(first), Path(second)
    if left.resolve() == right.resolve():
        return True
    try:
        return left.samefile(right)
    except FileNotFoundError:
        return False
