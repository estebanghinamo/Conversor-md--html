# ADR-005: Tablas y descarte de líneas que son solo etiquetas HTML

**Estado:** Aceptado · **Fecha:** 2026-10-14

## Contexto
La spec §4.3 deja fuera "tablas complejas". El propio README del proyecto usa tablas simples con barras y bloques `<div align="center">`; al convertirlo, las tablas salían como texto con `|` y el `<div>` como texto escapado (ADR-003). Se pidió soportar tablas simples y no mostrar etiquetas HTML sueltas.

## Problema
Una tabla Markdown necesita mirar varias líneas a la vez (encabezado y fila de alineación), pero el lexer clasificaba cada línea por separado (ADR-001). Además, hay que decidir qué hacer con el HTML crudo sin abrir superficie de ataque.

## Opciones consideradas
1. Tablas: (a) reconocerlas en el lexer con un token `TABLE` multilínea, como ya hace con los bloques de código; (b) emitir tokens por fila y que el parser decida si forman tabla.
2. Alineación `:--`, `:-:`, `--:`: soportarla o ignorarla.
3. HTML crudo: dejarlo escapado y limpiar el README; descartar las líneas que son solo etiquetas; permitir etiquetas y atributos en lista blanca.

## Decisión
1. **Token `TABLE` multilínea en el lexer** (opción a). Una tabla es un encabezado con `|`, una fila de guiones con el mismo número de columnas y las filas siguientes hasta una línea en blanco u otro bloque. El token lleva las celdas crudas (`rows`) y la alineación (`aligns`); el parser resuelve el inline de cada celda. Las filas se ajustan al ancho del encabezado.
2. **Con alineación.** El AST suma `Table`, `TableRow` y `TableCell` (inmutables, ADR-002). El sanitizer exige filas del ancho de la tabla y normaliza `align` a `left`/`center`/`right`/`None`; el renderer emite `<table>`, `<thead>`, `<tbody>`, `<th>` y `<td>` con `align="..."`, escapando todo al imprimir (ADR-003) y validando `align` otra vez antes de ponerlo en un atributo.
3. **Descartar líneas que son solo etiquetas HTML** (`<div align="center">`, `</div>`): el lexer las trata como línea en blanco. Una línea con texto entre o alrededor de las etiquetas (`<b>x</b>`, `<script>alert(1)</script>`) no se descarta y sigue escapándose como texto. No se permite ninguna etiqueta ni atributo: sigue sin haber HTML crudo en la salida.
4. **Límites anti-DoS:** `MAX_TABLE_COLUMNS = 20` por tabla y `MAX_TABLE_CELLS = 100_000` en total; superarlos lanza `LexerError`.

## Consecuencias
- La spec §4.3 pasa de "tablas complejas" a "tablas con celdas combinadas, sin encabezado o con bloques dentro de las celdas": solo se soportan tablas simples estilo GitHub (celdas con inline).
- Descartar etiquetas sueltas oculta contenido que antes se veía como texto: una línea `<img src=...>` sola ya no aparece. Es seguro (no se ejecuta ni se emite nada) y se documenta en el README y en `docs/security.md`.
- El lexer deja de ser estrictamente "una línea, un token" para las tablas, igual que ya ocurría con los bloques de código; la lógica sigue siendo de escaneo lineal.
- El sanitizer y el renderer tienen un nodo más que recorrer y validar; cualquier nodo nuevo debe seguir ese patrón.
- No se permite HTML en lista blanca. Hacerlo requeriría una ADR nueva que revise ADR-003.
