# Seguridad de MarkForge

Todo input es no confiable. La seguridad del HTML vive solo en el sanitizer; las etapas anteriores solo acotan recursos.

## Topes de recursos (anti-DoS)

| Etapa | Constante | Valor | Al excederse |
|---|---|---|---|
| Lexer | `MAX_INPUT_LENGTH` | 2.000.000 caracteres | `LexerError` |
| Lexer | `MAX_LINE_LENGTH` | 100.000 caracteres | `LexerError` |
| Lexer | `MAX_LINES` | 200.000 líneas | `LexerError` |
| Parser | `MAX_NESTING_DEPTH` | 8 niveles de cita | `ParserError` |
| Inline | `MAX_INLINE_DEPTH` | 32 niveles de nodos inline | queda como texto |
| Inline | `MAX_DELIMITER_RUNS` | 2.000 runs de `*` o `~~` por texto | queda como texto |
| Inline | `MAX_OPEN_BRACKETS` | 1.000 corchetes abiertos | queda como texto |
| Inline | `MAX_URL_LENGTH` | 2.048 caracteres | no es link ni imagen |

El escaneo es lineal, con comparaciones de prefijo, pilas y búsquedas acotadas. No hay regex anidadas. Los tests de `tests/unit/test_lexer.py` y `tests/unit/test_inline.py` incluyen entradas patológicas.

Si una vez se supera `MAX_INLINE_DEPTH`, el resto del texto deja de formatearse (queda literal): así el costo de recalcular el contenido se paga una sola vez y no hay tiempo cuadrático.

Los límites de línea y de tamaño se vuelven a aplicar al contenido de cada cita anidada, por eso el peor caso de memoria es de unas 9 listas de tokens (ver ADR-001).

## Pendiente para el sanitizer
- Las URLs de links e imágenes llegan **crudas** al AST: validar esquema (bloquear `javascript:`, `data:`, `vbscript:`) y escapar.
- `CodeBlock.language` es el primer fragmento tras los backticks, sin validar: escaparlo o restringirlo (por ejemplo a `[A-Za-z0-9_+-]{1,32}`) antes de usarlo en `class="language-…"`.
- El texto de `Text`, `InlineCode`, `CodeBlock` y `Image.alt` también llega crudo: escapar HTML.
- Los recorridos recursivos del AST pueden asumir una profundidad máxima razonable (citas × nodos inline).
