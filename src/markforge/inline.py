"""Parser inline: convierte el texto de un bloque en nodos inline del AST.

Soporta código inline, énfasis (`*`), negrita (`**`), tachado (`~~`), links,
imágenes y escapes con barra invertida. Es parte de la etapa del parser: no genera
HTML ni decide seguridad (las URLs y el texto quedan crudos para el sanitizer).

El input es no confiable. Para evitar tiempos cuadráticos o recursión profunda,
el escaneo es lineal con una pila y todo lo que podría crecer sin control tiene
un tope; lo que lo excede se deja como texto literal.

Al superar `MAX_INLINE_DEPTH` una vez, el resto del texto deja de formatearse
(queda literal): así el costo de recalcular el contenido se paga una sola vez.
"""

import re
import unicodedata
from bisect import bisect_left
from dataclasses import dataclass
from typing import cast

from markforge.ast import (
    Emphasis,
    Image,
    Inline,
    InlineCode,
    Link,
    Strikethrough,
    Strong,
    Text,
)

MAX_INLINE_DEPTH = 32
MAX_DELIMITER_RUNS = 2_000
MAX_OPEN_BRACKETS = 1_000
MAX_URL_LENGTH = 2_048

_SPECIAL = re.compile(r"[\\`*~\[\]!]")
_BACKTICK_RUN = re.compile(r"`+")
_ESCAPABLE = frozenset("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
_STRIKE_RUN = 2


@dataclass(slots=True)
class _Node:
    node: Inline
    depth: int


@dataclass(slots=True)
class _Delim:
    char: str
    count: int
    can_open: bool
    can_close: bool


@dataclass(slots=True)
class _Bracket:
    image: bool


_Item = _Node | _Delim | _Bracket


def parse_inline(text: str) -> tuple[Inline, ...]:
    """Devuelve los nodos inline de `text` (vacío si no hay texto)."""
    if not text:
        return ()
    return _Scanner(text).run()


def _is_space(char: str) -> bool:
    return char == "" or char.isspace()


def _is_punctuation(char: str) -> bool:
    return char != "" and unicodedata.category(char)[0] in "PS"


def _flanking(text: str, start: int, end: int) -> tuple[bool, bool]:
    """Devuelve (puede_abrir, puede_cerrar) para el run de delimitadores."""
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    before_space, after_space = _is_space(before), _is_space(after)
    before_punct, after_punct = _is_punctuation(before), _is_punctuation(after)
    left = not after_space and (not after_punct or before_space or before_punct)
    right = not before_space and (not before_punct or after_space or after_punct)
    return left, right


def _plain_text(nodes: tuple[Inline, ...]) -> str:
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, Text | InlineCode):
            parts.append(node.value)
        elif isinstance(node, Image):
            parts.append(node.alt)
        else:
            parts.append(_plain_text(node.children))
    return "".join(parts)


class _Scanner:
    def __init__(self, text: str) -> None:
        self.text = text
        self.out: list[_Item] = []
        self.buf: list[str] = []
        self.delims: list[int] = []
        self.brackets: list[int] = []
        self.inactive_below = 0
        self.delim_runs = 0
        self.frozen = False
        self.code_runs: dict[int, list[int]] | None = None

    def run(self) -> tuple[Inline, ...]:
        text = self.text
        pos = 0
        while (match := _SPECIAL.search(text, pos)) is not None:
            start = match.start()
            self.buf.append(text[pos:start])
            pos = self._dispatch(text[start], start)
        self.buf.append(text[pos:])
        self._flush()
        return self._children(self.out)[0]

    def _dispatch(self, char: str, pos: int) -> int:
        if char == "\\":
            return self._escape(pos)
        if char == "`":
            return self._code_span(pos)
        if char in "*~":
            return self._delimiter(char, pos)
        if char == "[":
            return self._open_bracket(pos, pos + 1, image=False)
        if char == "]":
            return self._close_bracket(pos)
        if self.text.startswith("![", pos):
            return self._open_bracket(pos, pos + 2, image=True)
        self.buf.append("!")
        return pos + 1

    def _flush(self) -> None:
        value = "".join(self.buf)
        self.buf.clear()
        if value:
            self.out.append(_Node(Text(value), 0))

    def _escape(self, pos: int) -> int:
        following = self.text[pos + 1 : pos + 2]
        if following and following in _ESCAPABLE:
            self.buf.append(following)
            return pos + 2
        self.buf.append("\\")
        return pos + 1

    def _run_end(self, char: str, pos: int) -> int:
        end = pos
        while end < len(self.text) and self.text[end] == char:
            end += 1
        return end

    def _code_span(self, pos: int) -> int:
        end = self._run_end("`", pos)
        length = end - pos
        closer = self._closing_backticks(length, end)
        if closer is None:
            self.buf.append("`" * length)
            return end
        content = self.text[end:closer].replace("\n", " ")
        if len(content) > 1 and content[0] == content[-1] == " " and content.strip(" "):
            content = content[1:-1]
        self._flush()
        self.out.append(_Node(InlineCode(content), 0))
        return closer + length

    def _closing_backticks(self, length: int, after: int) -> int | None:
        if self.code_runs is None:
            self.code_runs = {}
            for run in _BACKTICK_RUN.finditer(self.text):
                self.code_runs.setdefault(len(run.group()), []).append(run.start())
        starts = self.code_runs.get(length, [])
        index = bisect_left(starts, after)
        return starts[index] if index < len(starts) else None

    def _delimiter(self, char: str, pos: int) -> int:
        end = self._run_end(char, pos)
        count = end - pos
        can_open, can_close = _flanking(self.text, pos, end)
        usable = (can_open or can_close) and (char == "*" or count == _STRIKE_RUN)
        if not usable or self.frozen or self.delim_runs >= MAX_DELIMITER_RUNS:
            self.buf.append(self.text[pos:end])
            return end
        self.delim_runs += 1
        self._flush()
        self._push_delimiter(_Delim(char, count, can_open, can_close))
        return end

    def _push_delimiter(self, delim: _Delim) -> None:
        if delim.can_close:
            while delim.count > 0:
                opener = self._find_opener(delim)
                if opener is None or not self._wrap(opener, delim):
                    break
        if delim.count == 0:
            return
        if delim.can_open:
            self.out.append(delim)
            self.delims.append(len(self.out) - 1)
        else:
            self.out.append(_Node(Text(delim.char * delim.count), 0))

    def _find_opener(self, closer: _Delim) -> int | None:
        barrier = self.brackets[-1] if self.brackets else -1
        for position in range(len(self.delims) - 1, -1, -1):
            index = self.delims[position]
            if index < barrier:
                return None
            candidate = self.out[index]
            if (
                isinstance(candidate, _Delim)
                and candidate.char == closer.char
                and candidate.can_open
            ):
                return position
        return None

    def _wrap(self, position: int, closer: _Delim) -> bool:
        index = self.delims[position]
        opener = cast(_Delim, self.out[index])
        use = 2 if opener.count >= 2 and closer.count >= 2 else 1
        children, depth = self._children(self.out[index + 1 :])
        if depth + 1 > MAX_INLINE_DEPTH:
            self.frozen = True
            return False
        node: Inline
        if closer.char == "~":
            node = Strikethrough(children)
        elif use == 2:
            node = Strong(children)
        else:
            node = Emphasis(children)
        del self.out[index + 1 :]
        self.out.append(_Node(node, depth + 1))
        del self.delims[position + 1 :]
        opener.count -= use
        closer.count -= use
        if opener.count == 0:
            del self.out[index]
            del self.delims[position]
        return True

    def _open_bracket(self, pos: int, end: int, *, image: bool) -> int:
        if self.frozen or len(self.brackets) >= MAX_OPEN_BRACKETS:
            self.buf.append(self.text[pos:end])
            return end
        self._flush()
        self.out.append(_Bracket(image))
        self.brackets.append(len(self.out) - 1)
        return end

    def _close_bracket(self, pos: int) -> int:
        if not self.brackets:
            self.buf.append("]")
            return pos + 1
        self._flush()
        index = self.brackets[-1]
        bracket = cast(_Bracket, self.out[index])
        active = not self.frozen and (
            bracket.image or len(self.brackets) - 1 >= self.inactive_below
        )
        destination = self._destination(pos + 1) if active else None
        if destination is not None:
            end = self._close_with_destination(index, bracket, *destination)
            if end is not None:
                return end
        self._discard_bracket(index, bracket)
        self.buf.append("]")
        return pos + 1

    def _destination(self, start: int) -> tuple[str, int] | None:
        if self.text[start : start + 1] != "(":
            return None
        close = self.text.find(")", start + 1, start + 2 + MAX_URL_LENGTH)
        if close < 0:
            return None
        url = self.text[start + 1 : close]
        if not url or any(char.isspace() for char in url):
            return None
        return url, close + 1

    def _close_with_destination(
        self, index: int, bracket: _Bracket, url: str, end: int
    ) -> int | None:
        children, depth = self._children(self.out[index + 1 :])
        node: Inline
        if bracket.image:
            node, node_depth = Image(url, _plain_text(children)), 0
        elif depth + 1 > MAX_INLINE_DEPTH:
            self.frozen = True
            return None
        else:
            node, node_depth = Link(url, children), depth + 1
        del self.out[index:]
        while self.delims and self.delims[-1] > index:
            self.delims.pop()
        self.brackets.pop()
        self.inactive_below = (
            min(self.inactive_below, len(self.brackets)) if bracket.image else len(self.brackets)
        )
        self.out.append(_Node(node, node_depth))
        return end

    def _discard_bracket(self, index: int, bracket: _Bracket) -> None:
        self.brackets.pop()
        self.inactive_below = min(self.inactive_below, len(self.brackets))
        self.out[index] = _Node(Text("![" if bracket.image else "["), 0)

    def _children(self, items: list[_Item]) -> tuple[tuple[Inline, ...], int]:
        """Convierte items en nodos; delimitadores y corchetes sin resolver son texto."""
        result: list[Inline] = []
        pending: list[str] = []
        depth = 0
        for item in items:
            if isinstance(item, _Node):
                if isinstance(item.node, Text):
                    pending.append(item.node.value)
                    continue
                if pending:
                    result.append(Text("".join(pending)))
                    pending.clear()
                result.append(item.node)
                depth = max(depth, item.depth)
            elif isinstance(item, _Delim):
                pending.append(item.char * item.count)
            else:
                pending.append("![" if item.image else "[")
        if pending:
            result.append(Text("".join(pending)))
        return tuple(result), depth
