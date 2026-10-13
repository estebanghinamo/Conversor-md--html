"""Parser: consume tokens del lexer y construye el AST.

Esta etapa agrupa los tokens de línea en bloques (párrafos, listas, citas). No
genera HTML ni decide seguridad: el contenido del AST sigue siendo crudo.
"""

from collections.abc import Sequence

from markforge.ast import (
    Block,
    BlockQuote,
    CodeBlock,
    Document,
    Heading,
    HorizontalRule,
    List,
    ListItem,
    Paragraph,
)
from markforge.errors import ParserError
from markforge.inline import parse_inline
from markforge.lexer import Token, TokenType, tokenize

MAX_NESTING_DEPTH = 8


def parse(tokens: Sequence[Token]) -> Document:
    """Construye el `Document`; lanza `ParserError` si la cita anidada supera el límite."""
    return Document(_parse_blocks(tokens, 0))


def _parse_blocks(tokens: Sequence[Token], depth: int) -> tuple[Block, ...]:
    blocks: list[Block] = []
    index = 0
    while index < len(tokens):
        if tokens[index].type is TokenType.BLANK:
            index += 1
            continue
        block, index = _parse_block(tokens, index, depth)
        blocks.append(block)
    return tuple(blocks)


def _parse_block(tokens: Sequence[Token], index: int, depth: int) -> tuple[Block, int]:
    token = tokens[index]
    match token.type:
        case TokenType.HEADING:
            return Heading(token.level, parse_inline(token.value)), index + 1
        case TokenType.HORIZONTAL_RULE:
            return HorizontalRule(), index + 1
        case TokenType.CODE_BLOCK:
            return CodeBlock(token.value, token.language), index + 1
        case TokenType.BLOCKQUOTE:
            return _parse_blockquote(tokens, index, depth)
        case TokenType.LIST_ITEM:
            return _parse_list(tokens, index)
        case _:
            return _parse_paragraph(tokens, index)


def _parse_paragraph(tokens: Sequence[Token], start: int) -> tuple[Paragraph, int]:
    end = start + 1
    while end < len(tokens) and tokens[end].type is TokenType.TEXT:
        end += 1
    text = "\n".join(token.value for token in tokens[start:end])
    return Paragraph(parse_inline(text)), end


def _parse_blockquote(tokens: Sequence[Token], start: int, depth: int) -> tuple[BlockQuote, int]:
    if depth >= MAX_NESTING_DEPTH:
        msg = f"cita anidada más de {MAX_NESTING_DEPTH} niveles (línea {tokens[start].line})"
        raise ParserError(msg)
    end = start
    while end < len(tokens) and tokens[end].type is TokenType.BLOCKQUOTE:
        end += 1
    content = "\n".join(token.value for token in tokens[start:end])
    return BlockQuote(_parse_blocks(tokenize(content), depth + 1)), end


def _parse_list(tokens: Sequence[Token], start: int) -> tuple[List, int]:
    ordered = tokens[start].ordered
    items: list[ListItem] = []
    index = start
    while True:
        item_index = _skip_blanks(tokens, index)
        if item_index >= len(tokens):
            break
        token = tokens[item_index]
        if token.type is not TokenType.LIST_ITEM or token.ordered != ordered:
            break
        items.append(_parse_list_item(token))
        index = item_index + 1
    return List(ordered, tuple(items)), index


def _skip_blanks(tokens: Sequence[Token], index: int) -> int:
    while index < len(tokens) and tokens[index].type is TokenType.BLANK:
        index += 1
    return index


def _parse_list_item(token: Token) -> ListItem:
    inline = parse_inline(token.value)
    return ListItem((Paragraph(inline),) if inline else ())
