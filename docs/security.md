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

## Sanitizer (política, ver ADR-003)
- **URLs de links e imágenes:** lista blanca de esquemas `http`, `https` y `mailto`, más URLs relativas. Se rechazan vacías, de más de 2.048 caracteres o con espacios, barras invertidas, caracteres de control o de formato. Las URLs relativas al protocolo (`//host`) se permiten: pueden enlazar o cargar recursos externos, igual que cualquier `http(s)`. Un link bloqueado queda como su contenido; una imagen bloqueada, como su `alt`.
- **`CodeBlock.language`:** solo `[A-Za-z0-9_+-]{1,32}`; si no, se descarta.
- **Texto:** se eliminan los caracteres de control (salvo salto de línea y tab). Se eliminan también los overrides y aislamientos bidi (U+202A–202E, U+2066–2069) para evitar spoofing visual; otros caracteres de formato, como el espacio de ancho cero, se conservan en el texto.
- **Nodos desconocidos y AST de más de 64 niveles:** `SanitizationError`.

## Contrato con el renderer (pendiente de implementar)
El sanitizer **no escapa HTML**. El renderer debe, una sola vez al imprimir:
- escapar `& < > " '` en todo texto, `InlineCode`, `CodeBlock`, `alt` y en los valores de `href` y `src`;
- emitir `language` solo como nombre de clase;
- tolerar contenedores sin hijos (por ejemplo, énfasis vacío tras quitar un link bloqueado).

Entradas como `javascript&colon;x` pasan el sanitizer porque no tienen esquema: solo son inofensivas si el renderer escapa el `&`.

## CLI

- **Lectura acotada:** se leen como máximo `MAX_INPUT_BYTES` (4 bytes por carácter del límite del lexer) antes de decodificar. Si hay más, sale con código 1 sin cargar el resto en memoria.
- **Codificación:** UTF-8 estricto (se ignora un BOM inicial); si es inválido, código 1.
- **Salida:** solo se escribe si la conversión terminó bien, así que un error no toca el archivo de salida. Se sobrescribe en el lugar (no es atómico) y se rechaza que sea el mismo archivo que la entrada, incluso mediante symlinks o hard links.
- **Mensajes de error:** solo incluyen la ruta que pasó el usuario y el motivo del sistema (o el límite superado); nunca el contenido del input ni trazas.
- **Códigos de salida:** 0 éxito, 1 input inválido, 2 error de E/S o de uso.
- **`--standalone`:** `page.py` envuelve el HTML ya renderizado (sin tocar el pipeline). El único dato propio es `--title`, que se escapa; un título con bytes inválidos sale con código 1. La página lleva un CSP por `<meta>` sin scripts (`default-src 'none'`, `base-uri 'none'`, `form-action 'none'`).

## Riesgos aceptados

| Aviso | Dónde | Decisión |
|---|---|---|
| SonarCloud `pythonsecurity:S8707` (Path Traversal) | `cli._write_output()` | Aceptado en Sonar (PRs #8 y #9): `--output` escribe donde indica el usuario, por diseño. Mitigaciones y alternativas descartadas en [ADR-004](adr/004-cli-io-policy.md). |
| Imágenes remotas en `--standalone` (`img-src http: https:`) | `page._CSP` | Coherente con la lista blanca del sanitizer (`http`, `https`): abrir el HTML puede cargar imágenes externas (tracking, fuga de IP). No es XSS. |
| El título de `--standalone` no filtra caracteres bidi ni de control | `page.wrap_page()` | El escape HTML es correcto para el contexto de `<title>`; solo habría spoofing visual en la pestaña. |
| La escritura del archivo de salida no es atómica | `cli._write_output()` | Se escribe en el lugar, solo después de convertir con éxito. Un corte a mitad de escritura (disco lleno, `kill`) puede dejar el archivo incompleto. |
| Las URLs de links e imágenes se cortan en el primer `)` | `inline.py` | Limitación de corrección, no de seguridad: la URL cortada se valida igual en el sanitizer. |
