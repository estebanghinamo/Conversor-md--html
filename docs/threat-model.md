# Modelo de amenazas de MarkForge

Qué se protege, de quién y con qué. Los límites exactos, la política del sanitizer y los riesgos aceptados están en [security.md](security.md); aquí solo se ordenan por amenaza.

## Alcance y supuestos

- **Qué es:** una biblioteca (`convert()`) y una CLI que reciben Markdown y devuelven un fragmento HTML (o una página con `--standalone`).
- **Atacante:** quien controla el texto de entrada (un usuario que sube Markdown, un archivo descargado). Se asume que **todo input es no confiable**. No se asume control del entorno donde se ejecuta ni de quien invoca la CLI.
- **Qué se protege:** (1) el navegador de quien abre el HTML (sin XSS), (2) la disponibilidad del proceso que convierte (sin consumo descontrolado de CPU o memoria) y (3) los archivos del usuario de la CLI.
- **Frontera de confianza:** el texto Markdown entra por `convert()` o por la CLI. Todo lo que cruza esa frontera es crudo hasta salir del sanitizer.
- **Fuera de alcance:** la seguridad de la aplicación que incrusta el HTML (CSP del sitio, cookies), un atacante con acceso de escritura al repositorio o a los runners, y el contenido de los sitios a los que apuntan los enlaces.

## Amenazas y mitigaciones

| # | Amenaza | Vector | Mitigación | Verificación |
|---|---|---|---|---|
| T1 | **XSS por esquema de URL** | `[x](javascript:...)`, `data:`, `vbscript:`, mayúsculas, espacios, caracteres de control o entidades | Lista blanca de esquemas (`http`, `https`, `mailto`, relativas); lo bloqueado queda como texto | Tests XSS de integración, golden tests y propiedad "el HTML solo usa tags y atributos de la lista cerrada" |
| T2 | **XSS por HTML crudo** | `<script>`, `<img onerror=...>` en el texto | No se emite HTML del usuario: se escapa como texto. Las líneas solo-etiquetas se descartan | Tests XSS y propiedad de escape único |
| T3 | **Inyección por atributos** | `language` del bloque de código, `align` de tablas, `href`, `src`, `alt` | `language` limitado a `[A-Za-z0-9_+-]{1,32}`; `align` solo a valores fijos; el renderer escapa `& < > " '` en todo valor de atributo | Tests del sanitizer y del renderer; propiedad del sanitizer idempotente |
| T4 | **Doble escape o escape omitido** | Decisiones de seguridad repartidas entre etapas | Una sola capa decide (sanitizer) y una sola escapa (renderer), una vez | Propiedad "el escape ocurre exactamente una vez" |
| T5 | **DoS por tiempo cuadrático o ReDoS** | Delimitadores `*` sin cerrar, corchetes anidados, líneas largas | Escaneo lineal con pila, sin regex anidadas; topes y degradación a texto literal. Un hallazgo real (22 s con 46 KB) se corrigió a 0,08 s | Tests de entradas patológicas, benchmarks (crecimiento ~lineal) y fuzzing del lexer |
| T6 | **DoS por tamaño o profundidad** | Input enorme, muchas líneas, citas o listas anidadas, tablas gigantes | Topes en lexer, parser, sanitizer y renderer (ver [security.md](security.md)); la CLI lee a lo sumo `MAX_INPUT_BYTES` | Tests de límites exactos y fuzzing |
| T7 | **Sobrescritura de archivos** | `--output` apuntando al archivo de entrada, también vía symlink o hard link | Se compara con `samefile` y se rechaza; solo se escribe si la conversión terminó bien | Tests de la CLI. Riesgo aceptado: `--output` escribe donde indica el usuario ([ADR-004](adr/004-cli-io-policy.md)) |
| T8 | **Fuga de información** | Mensajes de error con contenido del input; imágenes remotas (tracking) | Los errores solo llevan la ruta del usuario y el motivo, nunca el contenido ni trazas. Las imágenes `http(s)` se permiten por diseño | Tests de la CLI. Riesgo aceptado: tracking por imágenes remotas |
| T9 | **Spoofing visual** | Caracteres bidi (U+202A–202E, U+2066–2069) | El sanitizer los elimina del texto. El título de `--standalone` no los filtra (riesgo aceptado) | Tests del sanitizer |
| T10 | **Cadena de suministro** | Dependencia o imagen comprometida | Cero dependencias en runtime; `uv.lock` versionado; pip-audit, Dependency Review, Dependabot; imagen Docker no-root con base fijada por digest, Hadolint y Trivy; SBOM CycloneDX; Gitleaks | Workflows `security.yml`, `docker.yml`, `sbom.yml` |

## Defensa en profundidad

Aunque solo el sanitizer decide, otras capas fallan de forma segura:

- el renderer rechaza nodos desconocidos y árboles demasiado profundos (`RenderError`);
- `--standalone` añade un CSP sin scripts (`default-src 'none'`) a la página completa;
- la CLI sale con código distinto de 0 ante cualquier error y no deja salidas parciales de una conversión fallida.

## Riesgos residuales

Los riesgos aceptados (S8707 de Sonar en `--output`, imágenes remotas, título sin filtro bidi, escritura no atómica, URLs cortadas en el primer `)`) están en la tabla de [security.md](security.md#riesgos-aceptados) con su justificación. Si alguno deja de ser aceptable, se registra una ADR.

## Evidencia de pruebas

Las pruebas no demuestran ausencia de fallos, pero acotan la confianza: tests unitarios, de integración y golden con *payloads* XSS reales; propiedades con Hypothesis; mutation testing (90,6 % en la corrida del 14/10/2026) y fuzzing del lexer sin fallos. Detalle y cifras en [testing.md](testing.md).
