# Guía de contribución

Gracias por querer aportar. Esta guía cubre cómo preparar el entorno, verificar un cambio y qué se espera de un PR. Para entender el diseño, empieza por [architecture.md](architecture.md).

## Entorno

Requiere Python 3.12+ y [uv](https://docs.astral.sh/uv/).

```bash
uv sync                 # crea .venv e instala dependencias desde uv.lock
uv run markforge --version
```

En Windows, si `uv` no está en el PATH, se puede usar como módulo: `python -m uv sync`.

## Verificar un cambio

Antes de abrir un PR deben pasar, en este orden:

```bash
uv run ruff format --check . && uv run ruff check .
uv run mypy
uv run pytest --cov -q          # cobertura mínima 90 % (hoy 100 %)
```

Mientras desarrollas, basta con tests puntuales (`uv run pytest tests/unit/test_lexer.py -k nombre`). Las pruebas de propiedades, el mutation testing y el fuzzing se describen en [testing.md](testing.md); no corren en cada PR.

`pre-commit` aplica ruff, formato y comprobaciones de archivos antes de cada commit (`uv run pre-commit install`).

## Reglas del código

- **Respeta el pipeline.** Cada etapa tiene una sola responsabilidad (ver [architecture.md](architecture.md)). La seguridad se decide solo en el sanitizer y el escape se hace solo en el renderer.
- **Todo input es no confiable.** No agregues HTML crudo a la salida ni valides seguridad fuera del sanitizer.
- **Sin regex anidadas.** Prefiere escaneo lineal, pilas y búsquedas acotadas; todo lo que pueda crecer lleva un tope.
- **Sin dependencias nuevas en runtime.** Las de desarrollo requieren justificación en el PR.
- **Tipos estrictos:** `mypy --strict`, sin `Any`, y excepciones específicas (nunca `except Exception: pass`).
- **Caracteres Unicode peligrosos** (bidi, NBSP, de control): constrúyelos con `chr()`, nunca literales ni con secuencias `\u` en el código. Semgrep y Sonar los bloquean.
- **Todo código nuevo lleva tests.** Un cambio de seguridad se documenta además en [security.md](security.md).

## Agregar una sintaxis nueva

1. Decide en qué etapa vive (bloque en el lexer, inline en `inline.py`) y recorre el pipeline en orden: lexer → parser/AST → sanitizer → renderer.
2. Escribe tests en cada capa tocada, un golden test (`tests/fixtures/`, `.md` ↔ `.html`) y, si el nodo lleva URLs, atributos o texto, casos de ataque en los tests de integración.
3. Si cambia una decisión estructural o una restricción permanente, escribe una ADR en `docs/adr/` (formato de las existentes) y avisa en el PR.
4. Actualiza la documentación afectada, sin duplicar lo que ya vive en otro archivo: enlázalo.

## Cambios de seguridad

El archivo `sanitizer.py` tiene un responsable asignado en `CODEOWNERS`, así que cualquier cambio ahí pide revisión explícita. Explica en el PR qué amenaza cubre o qué política cambia (sección *Security considerations* de la plantilla) y añade tests de regresión. Para reportar una vulnerabilidad, no abras un issue público: contacta con el mantenedor del repositorio.

## Ramas, commits y PRs

- Ramas desde `main` con prefijo: `feat/`, `fix/`, `docs/`, `chore/`, `ci/`.
- Commits convencionales, en una línea: `tipo: mensaje` (`feat: …`, `fix: …`, `docs: …`, `test: …`, `chore: …`, `ci: …`).
- Un PR por cambio coherente, con la plantilla del repositorio: qué cambió, por qué, comandos ejecutados con su resultado real, consideraciones de seguridad y si rompe algo.
- Los checks requeridos deben estar en verde: CI (ruff, mypy, pytest), CodeQL, Gitleaks y pip-audit. SonarCloud aplica además su Quality Gate.

## Herramientas que no corren en Windows

`mutmut` y Atheris se ejecutan en GitHub Actions (ubuntu), a mano desde *Actions* o cada semana, o en WSL/Docker. Para probar la imagen: `docker build -t markforge .` y `echo '# hola' | docker run --rm -i markforge`.
