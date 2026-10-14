"""Sanitizer: única etapa que decide seguridad. Devuelve un AST nuevo y seguro.

- Valida las URLs de links e imágenes con una lista blanca de esquemas.
- Un link bloqueado se reemplaza por su contenido; una imagen bloqueada, por su `alt`.
- Descarta lenguajes de bloques de código que no sean un identificador simple.
- Elimina caracteres de control del texto.
- Normaliza la alineación de tablas a left/center/right/None y exige filas del ancho de la tabla.
- Rechaza nodos desconocidos y AST demasiado profundos (`SanitizationError`).

El texto sigue sin escapar a HTML: lo escapa el renderer al imprimir, una sola vez.
"""

import re
import unicodedata

from markforge.ast import (
    Align,
    Block,
    BlockQuote,
    CodeBlock,
    Document,
    Emphasis,
    Heading,
    HorizontalRule,
    Image,
    Inline,
    InlineCode,
    Link,
    List,
    ListItem,
    Paragraph,
    Strikethrough,
    Strong,
    Table,
    TableCell,
    TableRow,
    Text,
)
from markforge.errors import SanitizationError

MAX_AST_DEPTH = 64
MAX_URL_LENGTH = 2_048
MAX_LANGUAGE_LENGTH = 32

ALLOWED_SCHEMES = frozenset({"http", "https", "mailto"})

# Rangos de control C0/C1 y overrides/aislamientos bidi; se arma con chr() para no
# dejar caracteres bidi literales en el código fuente.
_CONTROL_RANGES = ((0x00, 0x08), (0x0B, 0x1F), (0x7F, 0x9F), (0x202A, 0x202E), (0x2066, 0x2069))
_CONTROL_CHARS = re.compile(
    "[" + "".join(f"{re.escape(chr(lo))}-{re.escape(chr(hi))}" for lo, hi in _CONTROL_RANGES) + "]"
)
_LANGUAGE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_+-")
_PATH_DELIMITERS = "/?#"


def sanitize(document: Document) -> Document:
    """Devuelve una copia segura de `document`; no modifica el original."""
    return Document(tuple(_block(block, 1) for block in document.children))


def is_safe_url(url: str) -> bool:
    """True si la URL es relativa o usa un esquema de `ALLOWED_SCHEMES`."""
    if not url or len(url) > MAX_URL_LENGTH:
        return False
    if any(char == "\\" or char.isspace() or _is_invisible(char) for char in url):
        return False
    scheme = _scheme(url)
    return scheme is None or scheme in ALLOWED_SCHEMES


def _is_invisible(char: str) -> bool:
    return unicodedata.category(char) in ("Cc", "Cf")


def _scheme(url: str) -> str | None:
    for index, char in enumerate(url):
        if char == ":":
            return url[:index].lower()
        if char in _PATH_DELIMITERS:
            return None
    return None


def _clean(text: str) -> str:
    return _CONTROL_CHARS.sub("", text)


def _language(language: str | None) -> str | None:
    if language is None or not 0 < len(language) <= MAX_LANGUAGE_LENGTH:
        return None
    return language if all(char in _LANGUAGE_CHARS for char in language) else None


def _check_depth(depth: int) -> None:
    if depth > MAX_AST_DEPTH:
        msg = f"el AST excede {MAX_AST_DEPTH} niveles de profundidad"
        raise SanitizationError(msg)


def _unknown(node: object) -> SanitizationError:
    return SanitizationError(f"nodo desconocido: {type(node).__name__}")


def _block(block: Block, depth: int) -> Block:
    _check_depth(depth)
    match block:
        case Paragraph(children=children):
            return Paragraph(_inlines(children, depth + 1))
        case Heading(level=level, children=children):
            return Heading(level, _inlines(children, depth + 1))
        case HorizontalRule():
            return HorizontalRule()
        case CodeBlock(content=content, language=language):
            return CodeBlock(_clean(content), _language(language))
        case List(ordered=ordered, items=items):
            return List(ordered, tuple(_item(item, depth + 1) for item in items))
        case BlockQuote(children=children):
            return BlockQuote(tuple(_block(child, depth + 1) for child in children))
        case Table(aligns=aligns, header=header, rows=rows):
            return _table(aligns, header, rows, depth)
        case _:
            raise _unknown(block)


def _table(
    aligns: tuple[Align, ...], header: TableRow, rows: tuple[TableRow, ...], depth: int
) -> Table:
    safe_header = _row(header, len(aligns), depth + 1)
    safe_rows = tuple(_row(row, len(aligns), depth + 1) for row in rows)
    return Table(tuple(_align(align) for align in aligns), safe_header, safe_rows)


def _align(align: object) -> Align:
    match align:
        case "left" | "center" | "right":
            return align
        case _:
            return None


def _row(row: TableRow, columns: int, depth: int) -> TableRow:
    _check_depth(depth)
    if not isinstance(row, TableRow):
        raise _unknown(row)
    if len(row.cells) != columns:
        msg = "una fila de la tabla no tiene tantas celdas como columnas"
        raise SanitizationError(msg)
    return TableRow(tuple(_cell(cell, depth + 1) for cell in row.cells))


def _cell(cell: TableCell, depth: int) -> TableCell:
    _check_depth(depth)
    if not isinstance(cell, TableCell):
        raise _unknown(cell)
    return TableCell(_inlines(cell.children, depth + 1))


def _item(item: ListItem, depth: int) -> ListItem:
    _check_depth(depth)
    if not isinstance(item, ListItem):
        raise _unknown(item)
    return ListItem(tuple(_block(child, depth + 1) for child in item.children))


def _inlines(children: tuple[Inline, ...], depth: int) -> tuple[Inline, ...]:
    result: list[Inline] = []
    pending: list[str] = []
    for child in children:
        for node in _inline(child, depth):
            if isinstance(node, Text):
                pending.append(node.value)
                continue
            if pending:
                result.append(Text("".join(pending)))
                pending.clear()
            result.append(node)
    if pending:
        result.append(Text("".join(pending)))
    return tuple(result)


def _inline(node: Inline, depth: int) -> tuple[Inline, ...]:
    _check_depth(depth)
    match node:
        case Text(value=value):
            cleaned = _clean(value)
            return (Text(cleaned),) if cleaned else ()
        case InlineCode(value=value):
            return (InlineCode(_clean(value)),)
        case Emphasis(children=children):
            return (Emphasis(_inlines(children, depth + 1)),)
        case Strong(children=children):
            return (Strong(_inlines(children, depth + 1)),)
        case Strikethrough(children=children):
            return (Strikethrough(_inlines(children, depth + 1)),)
        case Link(url=url, children=children):
            safe_children = _inlines(children, depth + 1)
            return (Link(url, safe_children),) if is_safe_url(url) else safe_children
        case Image(url=url, alt=alt):
            cleaned_alt = _clean(alt)
            if is_safe_url(url):
                return (Image(url, cleaned_alt),)
            return (Text(cleaned_alt),) if cleaned_alt else ()
        case _:
            raise _unknown(node)
