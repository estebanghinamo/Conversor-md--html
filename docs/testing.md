# Testing de MarkForge

La cobertura mínima es 90 % (líneas y ramas); hoy es 100 %. Comandos reales en `COMMANDS.md`.

## Tipos de test

| Carpeta | Qué prueba |
|---|---|
| `tests/unit/` | Cada etapa aislada (lexer, parser, inline, sanitizer, renderer), la CLI y `convert()`. |
| `tests/integration/` | El pipeline completo: golden tests y payloads XSS de punta a punta. |
| `tests/property/` | Invariantes con Hypothesis sobre inputs generados. |
| `tests/fixtures/` | Pares `markdown/*.md` y `expected_html/*.html` de los golden tests. |

## Golden tests

Los fixtures se guardan con finales de línea LF (`.gitattributes`): la comparación es byte a byte y, en Windows con `core.autocrlf=true`, un checkout con CRLF rompería todos los golden.

Cada `tests/fixtures/markdown/x.md` se convierte con `convert()` y se compara con `tests/fixtures/expected_html/x.html`. Para agregar un caso se crean los dos archivos y se revisa a mano el HTML esperado antes de fijarlo.

## Tests de propiedades (Hypothesis)

Los inputs se generan de dos formas: texto libre y mezclas de fragmentos de Markdown, HTML y caracteres peligrosos (`<script>`, `javascript:`, `&#106;`, NUL, bidi, NBSP). Las propiedades principales:

- `convert` solo falla con `LexerError` o `ParserError`; nunca con `SanitizationError`, `RenderError` ni una excepción inesperada.
- El HTML generado solo contiene tags y atributos de una lista cerrada, sin comentarios ni declaraciones. Los `href` y `src` pasan un chequeo de URL escrito aparte del código de producción, para que el test no dependa del código que verifica.
- El texto con caracteres especiales se escapa exactamente una vez.
- El resultado es determinista, no cambia entre `\n` y `\r\n`, y el sanitizer es idempotente.
- El AST del parser nunca excede la profundidad que acepta el sanitizer, y el inline respeta `MAX_INLINE_DEPTH`.

Perfiles de Hypothesis (en `tests/conftest.py`):

| Perfil | Ejemplos por propiedad | Uso |
|---|---|---|
| `markforge` (por defecto) | 150 | desarrollo y CI |
| `deep` | 5.000 | búsqueda profunda antes de un release: `pytest tests/property --hypothesis-profile=deep` |

Hypothesis guarda en `.hypothesis/` (ignorado por git) los contraejemplos que encontró y los vuelve a probar. Un fallo se corrige arreglando el código y agregando un test unitario con el caso mínimo.

## Propiedades de fortaleza

Además de las propiedades generales, hay propiedades pensadas para matar mutaciones concretas (comprobadas rompiendo el código a propósito):

- **Round-trip del renderer** contra un parser HTML: atributos y texto de links, imágenes, código inline y bloques de código vuelven idénticos aunque el contenido sea agresivo (`<script>`, comillas, `&amp;`, bidi, NUL).
- **Sanitizer sobre ASTs arbitrarios**, sin pasar por los límites del parser: quita exactamente los caracteres prohibidos, conserva un link o imagen si y solo si la URL es segura y valida el lenguaje de los bloques de código.
- **Límites exactos** (justo debajo y justo en el tope) del lexer, el parser, el inline y el sanitizer.
- Un oráculo de URLs (`url_is_safe`) escrito aparte del código de producción, para que el test no dependa de lo que verifica.

## Verificar que los tests detectan fallos

Antes de confiar en una propiedad conviene romper el código a propósito (por ejemplo, quitar el escape del renderer o dejar pasar cualquier esquema en el sanitizer) y comprobar que algún test falla. Si no falla ninguno, la propiedad es demasiado débil. El mutation testing (`mutmut`) automatiza esto.

## Mutation testing (mutmut)

`mutmut` introduce cambios pequeños en `src/markforge/` (mutantes) y ejecuta los tests; si ninguno falla, el mutante *sobrevive* y señala un test débil. No corre en Windows: lo ejecuta [`mutation.yml`](../.github/workflows/mutation.yml) en ubuntu, a mano (*Actions > Mutation testing > Run workflow*) o cada lunes. El job falla si el score baja de 80 %.

Última corrida (14/10/2026): **90,6 %**, con 1.538 mutantes (1.363 muertos, 31 por timeout, 144 sobrevivientes, 0 sospechosos). Los sobrevivientes quedan en el artefacto `survivors.txt` de la corrida.

## Fuzzing (Atheris)

[`tests/fuzz/fuzz_lexer.py`](../tests/fuzz/fuzz_lexer.py) alimenta el lexer con bytes arbitrarios; solo es válido que tokenice o lance `LexerError`, cualquier otra excepción es un bug. Lo ejecuta [`fuzz.yml`](../.github/workflows/fuzz.yml) en ubuntu (Atheris no corre en Windows), a mano o cada lunes, con `-timeout=10` para detectar cuelgues. Un test de humo (`tests/unit/test_fuzz_harness.py`) comprueba el harness sin Atheris.

Primera corrida (14/10/2026, 300 s): más de 1,1 millones de ejecuciones a ~4.000 por segundo, cobertura saturada (154 puntos del lexer) y ningún fallo.

## Bugs que encontraron los tests de propiedades

- Un info string de un bloque de código con un carácter de control (por ejemplo U+001F) hacía `IndexError` en el lexer, porque `str.split()` también corta en esos caracteres. Corregido en el lexer.
