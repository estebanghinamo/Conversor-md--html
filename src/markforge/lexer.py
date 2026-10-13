"""Lexer: convierte Markdown en una lista de tokens de bloque, línea por línea.

No genera HTML ni conoce el AST. El Markdown inline (énfasis, código, links,
imágenes) se deja intacto en el valor de los tokens para que lo procese el parser.
El input es no confiable: el escaneo es lineal y tiene límites de tamaño.
"""

import string
from dataclasses import dataclass
from enum import Enum, auto
from typing import NamedTuple

from markforge.errors import LexerError

MAX_INPUT_LENGTH = 2_000_000
MAX_LINE_LENGTH = 100_000
MAX_LINES = 200_000

_MAX_INDENT = 3
_MAX_HEADING_LEVEL = 6
_MAX_ORDERED_DIGITS = 9
_MIN_FENCE_LENGTH = 3
_MIN_RULE_LENGTH = 3
_WHITESPACE = " \t"
_RULE_CHARS = "-*_"
_BULLET_CHARS = "-*+"


class TokenType(Enum):
    BLANK = auto()
    HEADING = auto()
    HORIZONTAL_RULE = auto()
    BLOCKQUOTE = auto()
    LIST_ITEM = auto()
    CODE_BLOCK = auto()
    TEXT = auto()


@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    value: str
    line: int
    level: int = 0
    ordered: bool = False
    language: str | None = None


class _Fence(NamedTuple):
    length: int
    language: str | None


def tokenize(source: str) -> list[Token]:
    """Tokeniza `source`; lanza `LexerError` si excede los límites de tamaño."""
    if len(source) > MAX_INPUT_LENGTH:
        msg = f"el input excede {MAX_INPUT_LENGTH} caracteres"
        raise LexerError(msg)
    lines = _split_lines(source)
    tokens: list[Token] = []
    index = 0
    while index < len(lines):
        fence = _open_fence(lines[index])
        if fence is None:
            tokens.append(_tokenize_line(lines[index], index + 1))
            index += 1
        else:
            token, index = _read_code_block(lines, index, fence)
            tokens.append(token)
    return tokens


def _split_lines(source: str) -> list[str]:
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines[-1] == "":
        lines.pop()
    if len(lines) > MAX_LINES:
        msg = f"el input excede {MAX_LINES} líneas"
        raise LexerError(msg)
    for number, line in enumerate(lines, start=1):
        if len(line) > MAX_LINE_LENGTH:
            msg = f"la línea {number} excede {MAX_LINE_LENGTH} caracteres"
            raise LexerError(msg)
    return lines


def _indent(line: str) -> int:
    stripped = line.lstrip(" ")
    if stripped.startswith("\t"):
        return _MAX_INDENT + 1
    return len(line) - len(stripped)


def _open_fence(line: str) -> _Fence | None:
    indent = _indent(line)
    if indent > _MAX_INDENT:
        return None
    body = line[indent:]
    length = len(body) - len(body.lstrip("`"))
    if length < _MIN_FENCE_LENGTH:
        return None
    info = body[length:].strip(_WHITESPACE)
    if "`" in info:
        return None
    # Solo espacio y tab separan palabras (`str.split()` también corta en controles).
    return _Fence(length, info.replace("\t", " ").split(" ", 1)[0] if info else None)


def _closes_fence(line: str, length: int) -> bool:
    if _indent(line) > _MAX_INDENT:
        return False
    body = line.strip(_WHITESPACE)
    return len(body) >= length and body.strip("`") == ""


def _read_code_block(lines: list[str], start: int, fence: _Fence) -> tuple[Token, int]:
    content: list[str] = []
    index = start + 1
    while index < len(lines):
        closed = _closes_fence(lines[index], fence.length)
        index += 1
        if closed:
            break
        content.append(lines[index - 1])
    token = Token(TokenType.CODE_BLOCK, "\n".join(content), start + 1, language=fence.language)
    return token, index


def _tokenize_line(line: str, number: int) -> Token:
    body = line.strip(_WHITESPACE)
    if not body:
        return Token(TokenType.BLANK, "", number)
    if _indent(line) <= _MAX_INDENT:
        for matcher in (_heading, _horizontal_rule, _blockquote, _list_item):
            token = matcher(body, number)
            if token is not None:
                return token
    return Token(TokenType.TEXT, body, number)


def _heading(body: str, number: int) -> Token | None:
    level = len(body) - len(body.lstrip("#"))
    if not 1 <= level <= _MAX_HEADING_LEVEL:
        return None
    rest = body[level:]
    if rest and rest[0] not in _WHITESPACE:
        return None
    return Token(
        TokenType.HEADING, _strip_closing_hashes(rest.strip(_WHITESPACE)), number, level=level
    )


def _strip_closing_hashes(text: str) -> str:
    trimmed = text.rstrip("#")
    if trimmed == text:
        return text
    if not trimmed:
        return ""
    if trimmed[-1] in _WHITESPACE:
        return trimmed.rstrip(_WHITESPACE)
    return text


def _horizontal_rule(body: str, number: int) -> Token | None:
    marks = body.replace(" ", "").replace("\t", "")
    if (
        len(marks) >= _MIN_RULE_LENGTH
        and marks[0] in _RULE_CHARS
        and marks.count(marks[0]) == len(marks)
    ):
        return Token(TokenType.HORIZONTAL_RULE, "", number)
    return None


def _blockquote(body: str, number: int) -> Token | None:
    if not body.startswith(">"):
        return None
    rest = body[1:]
    if rest.startswith(" "):
        rest = rest[1:]
    return Token(TokenType.BLOCKQUOTE, rest, number)


def _list_item(body: str, number: int) -> Token | None:
    if body[0] in _BULLET_CHARS and (len(body) == 1 or body[1] in _WHITESPACE):
        return Token(TokenType.LIST_ITEM, body[1:].strip(_WHITESPACE), number)
    digits = len(body) - len(body.lstrip(string.digits))
    marker_end = digits + 1
    if (
        1 <= digits <= _MAX_ORDERED_DIGITS
        and body[digits : digits + 1] == "."
        and body[marker_end : marker_end + 1] in ("", " ", "	")
    ):
        return Token(
            TokenType.LIST_ITEM, body[marker_end:].strip(_WHITESPACE), number, ordered=True
        )
    return None
