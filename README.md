# MarkForge

Biblioteca y herramienta de línea de comandos (CLI) en Python que transforma un subconjunto controlado de **Markdown** en **HTML** seguro.

> Estado: en desarrollo. El pipeline completo funciona; faltan Docker, SBOM, fuzzing y mutation testing. Ver `ESPECIFICACION_DEL_SISTEMA.md`.

## Pipeline

```
Markdown → Lexer → Tokens → Parser → AST → Sanitizer → Renderer → HTML
```

## Uso

```bash
markforge input.md                      # HTML por stdout
markforge input.md --output out.html    # HTML a un archivo
cat input.md | markforge                # lee de stdin ("-" también)
```

Códigos de salida: `0` éxito · `1` input inválido (error de MarkForge, UTF-8 inválido o demasiado grande) · `2` error de E/S o de uso.

Como biblioteca:

```python
from markforge import convert

html = convert("# Hola **mundo**")  # '<h1>Hola <strong>mundo</strong></h1>\n'
```

El HTML devuelto es un fragmento seguro: se escapa todo el texto y solo se permiten links `http`, `https`, `mailto` y relativos. Detalle de la política y de los límites de tamaño en `docs/security.md`.

## Desarrollo

Requiere Python 3.12+ y [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run markforge --version
uv run ruff format . && uv run ruff check .
uv run mypy
uv run pytest --cov
```

## Licencia

MIT
