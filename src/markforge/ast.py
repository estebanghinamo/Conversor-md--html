"""Nodos tipados e inmutables del AST.

El AST solo describe la estructura del documento: no valida seguridad ni genera
HTML. El contenido es siempre crudo (no confiable) hasta pasar por el sanitizer,
que devuelve un AST nuevo.
"""

from dataclasses import dataclass

MIN_HEADING_LEVEL = 1
MAX_HEADING_LEVEL = 6


@dataclass(frozen=True, slots=True)
class Text:
    value: str


@dataclass(frozen=True, slots=True)
class InlineCode:
    value: str


@dataclass(frozen=True, slots=True)
class Emphasis:
    children: tuple["Inline", ...]


@dataclass(frozen=True, slots=True)
class Strong:
    children: tuple["Inline", ...]


@dataclass(frozen=True, slots=True)
class Strikethrough:
    children: tuple["Inline", ...]


@dataclass(frozen=True, slots=True)
class Link:
    url: str
    children: tuple["Inline", ...]


@dataclass(frozen=True, slots=True)
class Image:
    url: str
    alt: str


Inline = Text | InlineCode | Emphasis | Strong | Strikethrough | Link | Image


@dataclass(frozen=True, slots=True)
class Paragraph:
    children: tuple[Inline, ...]


@dataclass(frozen=True, slots=True)
class Heading:
    level: int
    children: tuple[Inline, ...]

    def __post_init__(self) -> None:
        if type(self.level) is not int or not MIN_HEADING_LEVEL <= self.level <= MAX_HEADING_LEVEL:
            msg = f"nivel de heading fuera de rango: {self.level}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class HorizontalRule:
    pass


@dataclass(frozen=True, slots=True)
class CodeBlock:
    content: str
    language: str | None = None


@dataclass(frozen=True, slots=True)
class ListItem:
    children: tuple["Block", ...]


@dataclass(frozen=True, slots=True)
class List:
    ordered: bool
    items: tuple[ListItem, ...]


@dataclass(frozen=True, slots=True)
class BlockQuote:
    children: tuple["Block", ...]


Block = Paragraph | Heading | HorizontalRule | CodeBlock | List | BlockQuote


@dataclass(frozen=True, slots=True)
class Document:
    children: tuple[Block, ...]


Node = Document | ListItem | Block | Inline
