# MarkForge

Biblioteca y herramienta de línea de comandos (CLI) en Python que transforma un subconjunto controlado de **Markdown** en **HTML** seguro.

> Estado: en desarrollo inicial. El pipeline (Lexer → Parser → AST → Sanitizer → Renderer) se implementa de forma progresiva; ver `ESPECIFICACION_DEL_SISTEMA.md`.

## Pipeline

```
Markdown → Lexer → Tokens → Parser → AST → Sanitizer → Renderer → HTML
```

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
