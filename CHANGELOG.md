# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Mientras la versión sea 0.x, la API puede cambiar entre versiones menores.

## [0.1.0] - 2026-10-14

Primera versión: biblioteca y CLI que convierten un subconjunto de Markdown en HTML seguro, sin dependencias en runtime.

### Añadido

- **Pipeline completo** Lexer → Parser → AST → Sanitizer → Renderer, con AST inmutable ([ADR-001](docs/adr/001-parser-architecture.md), [ADR-002](docs/adr/002-ast-design.md)).
- **Markdown soportado:** encabezados, párrafos, listas, citas, reglas horizontales, bloques de código con *fences*, tablas simples con alineación, énfasis, negrita, tachado, código inline, enlaces, imágenes y escapes con `\` ([ADR-005](docs/adr/005-tables-and-html-tags.md)).
- **Seguridad:** lista blanca de esquemas de URL, escape único al imprimir, normalización de texto y topes de recursos contra DoS ([ADR-003](docs/adr/003-html-sanitization.md), [`docs/security.md`](docs/security.md)).
- **API pública** `convert()` y **CLI** `markforge` con entrada por archivo o stdin, `--output`, códigos de salida y lectura acotada ([ADR-004](docs/adr/004-cli-io-policy.md)).
- **`--standalone` y `--title`:** página HTML completa con estilos y una política CSP sin scripts.
- **Calidad:** tests unitarios, de integración, *golden* y de propiedades (Hypothesis), cobertura del 100 %, tipado `mypy --strict`, mutation testing con mutmut (90,6 %), fuzzing del lexer con Atheris y benchmarks con pytest-benchmark.
- **CI y seguridad:** Ruff, mypy, pytest y SonarCloud (Quality Gate); CodeQL, Semgrep, Gitleaks, pip-audit y Dependency Review; Dependabot.
- **Contenedor:** imagen Docker con usuario no-root y base fijada por digest, Hadolint, Trivy y SBOM CycloneDX con Syft.
- **Documentación:** README, [arquitectura](docs/architecture.md), [modelo de amenazas](docs/threat-model.md), [seguridad](docs/security.md), [testing](docs/testing.md), [guía de contribución](docs/contributing.md) y [política de seguridad](SECURITY.md).

### Limitaciones conocidas

- Subconjunto deliberado de Markdown, no todo CommonMark: sin HTML crudo, listas anidadas, tablas complejas ni enlaces con título.
- Las URLs de enlaces e imágenes se cortan en el primer `)`.
- Un guion bajo (`_`) queda como texto: el énfasis usa solo `*` y `**`.
- La escritura de `--output` no es atómica.
- Los riesgos aceptados están en [`docs/security.md`](docs/security.md#riesgos-aceptados).

[0.1.0]: https://github.com/estebanghinamo/Conversor-md--html/releases/tag/v0.1.0
