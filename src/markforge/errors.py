"""Excepciones específicas de MarkForge."""


class MarkdownError(Exception):
    """Error base de MarkForge."""


class LexerError(MarkdownError):
    """Error al tokenizar el Markdown."""


class ParserError(MarkdownError):
    """Error al construir el AST."""


class SanitizationError(MarkdownError):
    """Error al sanitizar el AST."""


class RenderError(MarkdownError):
    """Error al renderizar HTML."""
