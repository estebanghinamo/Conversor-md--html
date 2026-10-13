# ADR-001: Arquitectura Lexer/Parser

**Estado:** Aceptado · **Fecha:** 2026-10-13

## Contexto
La spec §6 define el pipeline Lexer → Tokens → Parser → AST. La lista conceptual de tokens (§6.2) mezcla estructura de bloque (`HEADING`, `LIST_ITEM`) con inline (`EMPHASIS`, `LINK`).

## Problema
Decidir qué reconoce el lexer y qué el parser, sin duplicar lógica ni abrir superficies de ReDoS sobre input no confiable.

## Opciones consideradas
1. El lexer reconoce bloques e inline en un solo pase.
2. El lexer reconoce solo estructura de bloque, línea por línea; el parser procesa el inline de los valores de texto.

## Decisión
Opción 2. El lexer emite un token por línea (`BLANK`, `HEADING`, `HORIZONTAL_RULE`, `BLOCKQUOTE`, `LIST_ITEM`, `TEXT`) y un único `CODE_BLOCK` por bloque con fences. No toca el contenido inline.
- Escaneo lineal con comparaciones de prefijo, sin regex anidadas.
- Límites: `MAX_INPUT_LENGTH`, `MAX_LINE_LENGTH` y `MAX_LINES`; al excederlos lanza `LexerError`.
- Solo espacio y tab cuentan como espacio en blanco.
- `\r\n` y `\r` se normalizan a `\n`.
- Sangría de 4 o más espacios (o tab) es texto: no hay code blocks indentados ni listas anidadas por ahora.
- Un fence sin cerrar llega hasta el final del documento.

## Consecuencias
- El lexer es simple y fácil de fuzzear.
- El parser asume el inline (énfasis, código, links, imágenes) y la agrupación de líneas en párrafos, listas y citas.
- `LIST_START` y `LIST_END` tampoco existen: el parser agrupa los `LIST_ITEM` consecutivos.
- `Token.language` es el info string sin validar; el sanitizer debe escaparlo o restringirlo antes de usarlo en HTML.
- Los tokens `EMPHASIS`, `STRONG`, `CODE`, `LINK`, `IMAGE` de §6.2 no existen en el lexer.
