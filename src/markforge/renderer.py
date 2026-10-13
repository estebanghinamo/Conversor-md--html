"""Renderer: convierte el AST sanitizado en un fragmento HTML.

No interpreta Markdown ni decide qué es seguro (eso es del sanitizer). Su
responsabilidad de seguridad es una sola: escapar todo texto y todo valor de
atributo al imprimir (`& < > " '`), exactamente una vez (ADR-003).
"""

from html import escape

from markforge.ast import (
    MAX_HEADING_LEVEL,
    MIN_HEADING_LEVEL,
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
    Text,
)
from markforge.errors import RenderError

MAX_RENDER_DEPTH = 64


def render(document: Document) -> str:
    """Devuelve el HTML de `document`; lanza `RenderError` ante un AST inválido.

    Exige un AST ya sanitizado (`sanitize`): el renderer escapa, pero no valida
    URLs ni esquemas. Pasarle un AST sin sanitizar emite `href` con cualquier esquema.
    """
    if not document.children:
        return ""
    return "\n".join(_block(block, 1) for block in document.children) + "\n"


def _check_depth(depth: int) -> None:
    if depth > MAX_RENDER_DEPTH:
        msg = f"el AST excede {MAX_RENDER_DEPTH} niveles de profundidad"
        raise RenderError(msg)


def _unknown(node: object) -> RenderError:
    return RenderError(f"nodo desconocido: {type(node).__name__}")


def _block(block: Block, depth: int) -> str:
    _check_depth(depth)
    match block:
        case Paragraph(children=children):
            return f"<p>{_inlines(children, depth + 1)}</p>"
        case Heading(level=level, children=children):
            # Defensivo: el nombre del tag se arma con `level`, que nunca debe ser arbitrario.
            if type(level) is not int or not MIN_HEADING_LEVEL <= level <= MAX_HEADING_LEVEL:
                msg = f"nivel de heading fuera de rango: {level}"
                raise RenderError(msg)
            return f"<h{level}>{_inlines(children, depth + 1)}</h{level}>"
        case HorizontalRule():
            return "<hr>"
        case CodeBlock(content=content, language=language):
            return _code_block(content, language)
        case List(ordered=ordered, items=items):
            return _list(ordered, items, depth)
        case BlockQuote(children=children):
            body = "".join(f"{_block(child, depth + 1)}\n" for child in children)
            return f"<blockquote>\n{body}</blockquote>"
        case _:
            raise _unknown(block)


def _code_block(content: str, language: str | None) -> str:
    attribute = f' class="language-{escape(language)}"' if language else ""
    body = f"{escape(content)}\n" if content else ""
    return f"<pre><code{attribute}>{body}</code></pre>"


def _list(ordered: bool, items: tuple[ListItem, ...], depth: int) -> str:
    tag = "ol" if ordered else "ul"
    body = "".join(f"{_list_item(item, depth + 1)}\n" for item in items)
    return f"<{tag}>\n{body}</{tag}>"


def _list_item(item: ListItem, depth: int) -> str:
    _check_depth(depth)
    if not isinstance(item, ListItem):
        raise _unknown(item)
    children = item.children
    if not children:
        return "<li></li>"
    if len(children) == 1 and isinstance(children[0], Paragraph):
        return f"<li>{_inlines(children[0].children, depth + 1)}</li>"
    body = "".join(f"{_block(child, depth + 1)}\n" for child in children)
    return f"<li>\n{body}</li>"


def _inlines(children: tuple[Inline, ...], depth: int) -> str:
    return "".join(_inline(child, depth) for child in children)


def _inline(node: Inline, depth: int) -> str:
    _check_depth(depth)
    match node:
        case Text(value=value):
            return escape(value)
        case InlineCode(value=value):
            return f"<code>{escape(value)}</code>"
        case Emphasis(children=children):
            return f"<em>{_inlines(children, depth + 1)}</em>"
        case Strong(children=children):
            return f"<strong>{_inlines(children, depth + 1)}</strong>"
        case Strikethrough(children=children):
            return f"<del>{_inlines(children, depth + 1)}</del>"
        case Link(url=url, children=children):
            href = escape(url)
            return f'<a href="{href}" rel="noopener noreferrer">{_inlines(children, depth + 1)}</a>'
        case Image(url=url, alt=alt):
            return f'<img src="{escape(url)}" alt="{escape(alt)}">'
        case _:
            raise _unknown(node)
