# ADR-003: Sanitización del AST

**Estado:** Aceptado · **Fecha:** 2026-10-13

## Contexto
El sanitizer es la única etapa que decide seguridad (spec §6.5). Recibe el AST del parser, con texto y URLs crudos, y lo entrega al renderer.

## Problema
Definir qué se bloquea, qué hace el sanitizer con lo bloqueado y quién escapa el HTML, sin duplicar escapes ni repartir decisiones de seguridad entre etapas.

## Opciones consideradas
1. Esquemas permitidos: `http`, `https`, `mailto` y URLs relativas, o solo `http` y `https`.
2. Con una URL bloqueada: reemplazar por texto o lanzar `SanitizationError`.
3. `CodeBlock.language`: validar contra un patrón y descartar, o escapar.
4. Escape de HTML: en el sanitizer (sobre el AST) o en el renderer al imprimir.

## Decisión
1. Lista blanca: `http`, `https`, `mailto` y URLs relativas. El esquema es lo que hay antes del primer `:` si aparece antes de `/`, `?` o `#`. Se rechazan URLs vacías, de más de 2.048 caracteres o con espacios, barras invertidas, caracteres de control o de formato (categorías Unicode `Cc` y `Cf`). Las URLs relativas al protocolo (`//host`) se permiten.
2. Un link bloqueado se reemplaza por su contenido; una imagen bloqueada, por su `alt` como texto. No se lanza error.
3. `language` solo se conserva si son 1 a 32 caracteres de `[A-Za-z0-9_+-]`; si no, se descarta.
4. El sanitizer devuelve un AST nuevo (el original no se modifica) y no escapa HTML. El renderer escapa **todo** texto y todo valor de atributo al imprimir (`& < > " '`), una sola vez. Esto es lo que hace inofensivas las URLs como `javascript&colon;x` o `&#106;avascript:x`.
5. Además normaliza (elimina caracteres de control, como NUL, retorno de carro y salto de página, salvo salto de línea y tab; también elimina los overrides y aislamientos bidi; otros caracteres de formato se conservan en el texto), rechaza nodos desconocidos y AST de más de `MAX_AST_DEPTH` niveles con `SanitizationError`.

## Consecuencias
- Una URL que parezca peligrosa nunca llega al renderer, pero la salida sigue siendo legible.
- El renderer depende del contrato de escapar siempre: sus tests deben verificarlo.
- Agregar un esquema permitido exige cambiar `ALLOWED_SCHEMES` y esta ADR.
- Es una lista blanca estricta: esquemas válidos pero poco comunes (`ftp`, `tel`) quedan bloqueados.
