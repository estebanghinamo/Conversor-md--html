# ADR-004: API pública y política de E/S de la CLI

**Estado:** Aceptado · **Fecha:** 2026-10-14

## Contexto
La spec §22 pide una CLI simple (archivo, stdin, `--output`, códigos de salida) y §23 errores útiles sin filtrar secretos. Además hacía falta una entrada única para usar el pipeline como biblioteca.

## Problema
Decidir dónde vive la conversión completa, qué códigos de salida usa la CLI y cuánto se restringe la escritura del archivo de salida, sabiendo que Sonar marca ese punto como "Path Traversal".

## Opciones consideradas
1. `convert()` en `markforge/__init__.py`, o en un módulo propio.
2. Códigos de salida: 0 éxito, 1 input inválido, 2 E/S o uso; o un único código de error.
3. Escritura de `--output`: libre en la ruta que indique el usuario; limitada al directorio actual; o exigir extensión `.html`.

## Decisión
1. `convert()` vive en `markforge/__init__.py` y compone `render(sanitize(parse(tokenize(x))))`. Es la única entrada recomendada de la API. La CLI solo hace E/S.
2. Códigos de salida: `0` éxito; `1` input inválido (error de MarkForge, UTF-8 inválido o demasiado grande); `2` error de E/S o de uso (los errores de uso de argparse también salen con 2).
3. `--output` escribe en la ruta que indica el usuario, sin restringirla: el usuario que ejecuta la herramienta es quien decide el destino, que es el propósito de la opción. Se mitiga así:
   - la lectura del input está acotada en bytes antes de decodificar;
   - solo se escribe si la conversión terminó bien;
   - se rechaza que la salida sea el mismo archivo que la entrada (incluso vía symlink o hard link, con `Path.samefile`);
   - los mensajes de error no incluyen el contenido del input ni trazas.

## Riesgo aceptado
SonarCloud reporta `pythonsecurity:S8707` ("Path Traversal via faulty LLM-supplied CLI arguments") en `cli._write_output()`. Se evaluó y **se aceptó** (estado *Accepted* en Sonar, con comentario) en los PRs #8 y #9, por ser comportamiento intencional de una herramienta de línea de comandos. Restringir la salida al directorio actual quitaría casos de uso legítimos sin garantía de que Sonar lo reconozca como saneamiento; exigir extensión no cambia el análisis.

## Consecuencias
- Si el aviso reaparece como "nuevo" en otro PR (por ejemplo, al cambiar las líneas de `_write_output`), hay que volver a aceptarlo en la interfaz de Sonar; no se arregla con código.
- Cambiar la política de escritura (restringir rutas) requiere una ADR nueva que reemplace esta.
- La API pública y los códigos de salida forman parte del contrato: cambiarlos es un cambio incompatible.
