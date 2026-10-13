# Especificación del Sistema — MarkForge

## 1. Propósito del documento

Este documento define la especificación técnica y de ingeniería del proyecto **MarkForge**.

Debe utilizarse como fuente de verdad para diseñar, implementar, configurar, probar, asegurar y documentar el sistema.

La implementación debe priorizar:

- simplicidad;
- claridad arquitectónica;
- mantenibilidad;
- seguridad por diseño;
- tipado estático;
- automatización;
- pruebas exhaustivas;
- calidad de código;
- trazabilidad;
- reproducibilidad;
- buenas prácticas de ingeniería de software.

**Regla principal:** no agregar complejidad o infraestructura que no tenga una justificación técnica concreta.

---

# 2. Idea del proyecto

## 2.1 Nombre

**MarkForge**

## 2.2 Descripción

MarkForge será una biblioteca y herramienta de línea de comandos (CLI) escrita en Python capaz de transformar un subconjunto controlado de **Markdown** en **HTML**.

El proyecto no busca implementar todo el estándar CommonMark. El objetivo es construir un parser pequeño, entendible y seguro que permita demostrar buenas prácticas de ingeniería de software.

Flujo conceptual:

```text
Markdown
   │
   ▼
Lexer
   │
   ▼
Tokens
   │
   ▼
Parser
   │
   ▼
AST
   │
   ▼
Sanitizer
   │
   ▼
HTML Renderer
   │
   ▼
HTML
```

## 2.3 Forma de uso

El proyecto tendrá dos interfaces principales:

### CLI

```bash
markforge README.md
```

```bash
markforge README.md --output README.html
```

```bash
cat README.md | markforge
```

```bash
markforge --version
```

```bash
markforge --help
```

### Biblioteca Python

Ejemplo conceptual:

```python
from markforge import render

html = render("# Hello")
```

---

# 3. Objetivos

## 3.1 Objetivos funcionales

MarkForge deberá:

1. Leer Markdown desde archivos.
2. Leer Markdown desde stdin.
3. Convertir Markdown a HTML.
4. Exponer una API Python sencilla.
5. Proporcionar errores controlados y comprensibles.
6. Escapar contenido HTML correctamente.
7. Validar URLs.
8. Evitar inyecciones HTML/XSS.
9. Mantener una arquitectura modular.
10. Permitir pruebas unitarias, de integración, de propiedades y fuzzing.

## 3.2 Objetivos de ingeniería

El proyecto debe demostrar:

- Clean Code.
- separación de responsabilidades;
- arquitectura modular;
- typing;
- testing avanzado;
- seguridad;
- análisis estático;
- automatización CI/CD;
- supply-chain security;
- reproducibilidad;
- documentación técnica;
- calidad medible.

---

# 4. Alcance funcional

## 4.1 Markdown de bloques

Implementar inicialmente:

- headings;
- párrafos;
- listas no ordenadas;
- listas ordenadas;
- blockquotes;
- horizontal rules;
- fenced code blocks.

Ejemplos:

```markdown
# Título
```

```markdown
- Item 1
- Item 2
```

```markdown
1. Primero
2. Segundo
```

```markdown
> Un bloque de cita
```

```markdown
---
```

```markdown
```python
print("hello")
```
```

## 4.2 Markdown inline

Implementar:

- texto plano;
- emphasis;
- strong;
- inline code;
- links;
- imágenes;
- escaping HTML;
- opcionalmente strikethrough.

Ejemplos:

```markdown
*texto*
```

```markdown
**texto**
```

```markdown
`codigo`
```

```markdown
[OpenAI](https://openai.com)
```

```markdown
![imagen](https://example.com/image.png)
```

## 4.3 Fuera de alcance

Inicialmente no implementar:

- todo CommonMark;
- tablas complejas;
- extensiones arbitrarias;
- plugins dinámicos;
- ejecución de código;
- JavaScript embebido;
- HTML arbitrario;
- backend web;
- frontend;
- base de datos;
- microservicios;
- Kubernetes;
- Terraform;
- Redis;
- Kafka;
- observabilidad distribuida;
- cloud deployment.

El proyecto debe permanecer pequeño y enfocado.

---

# 5. Tecnología principal

## 5.1 Lenguaje

**Python 3.12+**

La implementación debe utilizar:

- type hints;
- `dataclasses` cuando correspondan;
- `enum` cuando sea útil;
- excepciones específicas;
- APIs pequeñas y explícitas.

## 5.2 Gestión de dependencias

Utilizar:

**uv**

Objetivos:

- creación de entornos;
- instalación de dependencias;
- lockfile;
- builds reproducibles;
- ejecución de comandos.

Debe existir un lockfile versionado en el repositorio.

---

# 6. Arquitectura

La arquitectura principal será un pipeline:

```text
Input
  │
  ▼
Lexer
  │
  ▼
Token Stream
  │
  ▼
Parser
  │
  ▼
AST
  │
  ▼
Sanitizer
  │
  ▼
HTML Renderer
  │
  ▼
Output
```

## 6.1 Lexer

Responsabilidad:

- analizar el Markdown;
- reconocer estructuras;
- generar tokens;
- no generar HTML.

El lexer no debe conocer detalles del renderer.

## 6.2 Tokens

Los tokens representan elementos sintácticos detectados.

Ejemplos conceptuales:

```text
HEADING
TEXT
EMPHASIS
STRONG
CODE
LINK
IMAGE
LIST_START
LIST_END
LIST_ITEM
BLOCKQUOTE
HORIZONTAL_RULE
CODE_BLOCK
```

## 6.3 Parser

Responsabilidad:

- consumir tokens;
- validar estructura;
- construir el AST.

No debe generar HTML.

## 6.4 AST

El AST representa la estructura semántica del documento.

Ejemplo conceptual:

```text
Document
 ├── Heading
 │    └── Text
 ├── Paragraph
 │    ├── Text
 │    └── Strong
 │         └── Text
 └── List
      ├── ListItem
      └── ListItem
```

## 6.5 Sanitizer

Responsabilidad crítica de seguridad.

Debe:

- garantizar que el HTML quede escapado (la validación y la normalización las hace el sanitizer; el escape al imprimir lo hace el renderer, una sola vez, ver ADR-003);
- validar URLs;
- bloquear protocolos peligrosos;
- prevenir HTML injection;
- prevenir XSS;
- normalizar entradas cuando sea necesario.

Protocolos potencialmente peligrosos como:

```text
javascript:
data:
vbscript:
```

deben ser rechazados o tratados de manera segura según la política definida.

El sanitizer debe ser una etapa explícita del pipeline.

## 6.6 HTML Renderer

Responsabilidad:

- convertir el AST sanitizado en HTML;
- escapar todo texto y todo valor de atributo al imprimir (`& < > " '`), una sola vez;
- no interpretar Markdown;
- no realizar parsing;
- no tomar decisiones de seguridad que correspondan al sanitizer (qué URLs, esquemas y lenguajes son válidos).

---

# 7. Estructura del repositorio

```text
markforge/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── security.yml
│   │   ├── mutation.yml
│   │   ├── fuzz.yml
│   │   ├── docker.yml
│   │   └── sbom.yml
│   ├── dependabot.yml
│   ├── CODEOWNERS
│   ├── pull_request_template.md
│   └── ISSUE_TEMPLATE/
│
├── src/
│   └── markforge/
│       ├── __init__.py
│       ├── cli.py
│       ├── lexer.py
│       ├── parser.py
│       ├── ast.py
│       ├── sanitizer.py
│       ├── renderer.py
│       ├── errors.py
│       └── version.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── property/
│   ├── fuzz/
│   ├── fixtures/
│   │   ├── markdown/
│   │   └── expected_html/
│   └── conftest.py
│
├── benchmarks/
│
├── docs/
│   ├── architecture.md
│   ├── security.md
│   ├── testing.md
│   ├── contributing.md
│   ├── threat-model.md
│   └── adr/
│       ├── 001-parser-architecture.md
│       ├── 002-ast-design.md
│       └── 003-html-sanitization.md
│
├── Dockerfile
├── .dockerignore
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── README.md
├── LICENSE
└── SPECIFICATION.md
```

---

# 8. Calidad de código

## 8.1 Ruff

Utilizar **Ruff** para:

- linting;
- formatting.

Se debe evitar duplicar herramientas sin necesidad.

El formato debe validarse automáticamente en CI.

## 8.2 mypy

Utilizar **mypy** para análisis estático y tipado.

Objetivo:

- código fuertemente tipado;
- evitar `Any` innecesario;
- detectar inconsistencias antes de ejecutar el programa.

## 8.3 pre-commit

Utilizar **pre-commit** para automatizar validaciones antes de los commits.

Debe poder ejecutar, como mínimo:

- Ruff;
- validaciones básicas;
- detección de problemas comunes.

---

# 9. Testing

El testing es parte fundamental del proyecto.

## 9.1 pytest

Framework principal:

**pytest**

## 9.2 Coverage

Utilizar:

**pytest-cov**

Objetivo inicial:

```text
Coverage >= 90%
```

La cobertura debe considerar líneas y ramas cuando sea posible.

El porcentaje no debe utilizarse como sustituto de tests de calidad.

## 9.3 Unit tests

Cubrir individualmente:

- lexer;
- parser;
- AST;
- sanitizer;
- renderer;
- CLI;
- errores.

## 9.4 Integration tests

Probar el pipeline completo:

```text
Markdown
→ Lexer
→ Parser
→ AST
→ Sanitizer
→ Renderer
→ HTML
```

## 9.5 Golden tests

Utilizar fixtures:

```text
tests/fixtures/markdown/
tests/fixtures/expected_html/
```

Ejemplo:

```text
basic.md
basic.html
```

El test debe verificar que el Markdown produzca exactamente el HTML esperado.

## 9.6 Property-based testing

Utilizar:

**Hypothesis**

Propiedades deseables:

- el renderer nunca debe producir HTML inválido debido a inputs normales;
- entradas arbitrarias no deben provocar crashes inesperados;
- el sanitizer nunca debe permitir protocolos peligrosos;
- funciones críticas deben mantener invariantes definidas.

## 9.7 Mutation testing

Utilizar:

**mutmut**

Objetivo inicial:

```text
Mutation score >= 80%
```

El mutation testing debe utilizarse para detectar tests débiles.

## 9.8 Fuzzing

Utilizar:

**Atheris**

El fuzzing debe enfocarse principalmente en:

- lexer;
- parser;
- sanitizer.

Objetivo:

- detectar crashes;
- loops;
- errores inesperados;
- inputs malformados;
- problemas de seguridad.

El fuzzing no debe hacer que el CI normal sea excesivamente lento.

Por eso tendrá workflow separado.

## 9.9 Benchmarking

Utilizar:

**pytest-benchmark**

Medir:

- documentos pequeños;
- documentos medianos;
- documentos grandes;
- inputs con estructuras complejas.

El objetivo es detectar regresiones de rendimiento, no optimizar prematuramente.

---

# 10. Seguridad

La seguridad debe diseñarse desde la arquitectura.

## 10.1 Threat model

Documentar amenazas como:

- XSS;
- HTML injection;
- URL injection;
- protocolos peligrosos;
- inputs extremadamente grandes;
- inputs malformados;
- loops;
- consumo excesivo de CPU;
- consumo excesivo de memoria;
- dependencias vulnerables;
- secretos accidentalmente commiteados.

## 10.2 Seguridad del HTML

Todo texto proveniente del usuario debe tratarse como no confiable.

Ejemplo peligroso:

```html
<script>alert("XSS")</script>
```

El sistema no debe permitir que Markdown arbitrario genere HTML ejecutable.

## 10.3 URLs

Validar:

- esquema;
- formato;
- caracteres;
- valores peligrosos.

Se deben bloquear o sanitizar esquemas peligrosos.

## 10.4 Inputs grandes

Definir límites razonables cuando sea necesario.

Evitar algoritmos con complejidad innecesariamente alta.

---

# 11. Herramientas de seguridad

## 11.1 CodeQL

Utilizar **GitHub CodeQL** como SAST.

Objetivo:

- detectar vulnerabilidades;
- analizar data flow;
- identificar patrones inseguros.

## 11.2 Semgrep

Utilizar **Semgrep** como análisis complementario.

Debe detectar:

- patrones peligrosos;
- malas prácticas;
- vulnerabilidades específicas.

## 11.3 Gitleaks

Utilizar **Gitleaks** para detectar:

- API keys;
- tokens;
- contraseñas;
- secretos;
- credenciales accidentales.

## 11.4 pip-audit

Utilizar **pip-audit** para detectar vulnerabilidades conocidas en dependencias Python.

## 11.5 GitHub Dependency Review

Habilitar Dependency Review para Pull Requests.

Debe ayudar a detectar dependencias nuevas con problemas conocidos.

## 11.6 Dependabot

Configurar Dependabot para mantener actualizadas las dependencias.

---

# 12. Docker

Aunque el proyecto es principalmente local/development, debe existir una imagen Docker reproducible para demostrar buenas prácticas de containerización.

## Requisitos

- imagen base pequeña;
- dependencias mínimas;
- usuario no-root;
- `.dockerignore`;
- no incluir secretos;
- build reproducible cuando sea razonablemente posible.

Ejemplo conceptual:

```text
Dockerfile
    │
    ├── Build
    ├── Install dependencies
    ├── Copy application
    └── Run as non-root
```

## Herramientas

### Hadolint

Analizar el Dockerfile.

### Trivy

Analizar:

- vulnerabilidades;
- paquetes;
- configuración;
- imagen final.

---

# 13. Software Bill of Materials

Generar un **SBOM**.

Herramienta:

**Syft**

Formato preferido:

- CycloneDX;
- o SPDX.

El SBOM debe generarse automáticamente en GitHub Actions y quedar disponible como artifact.

---

# 14. Supply Chain Security

La cadena de suministro debe considerarse parte del proyecto.

Utilizar:

- lockfile;
- dependencias fijadas;
- Dependabot;
- Dependency Review;
- pip-audit;
- SBOM;
- análisis de contenedores;
- firma de artefactos cuando corresponda.

## Cosign

Evaluar/utilizar **Cosign** para firmar artefactos o imágenes cuando exista un artefacto distribuible que justifique la firma.

No introducir complejidad criptográfica innecesaria si no existe un artefacto que firmar.

---

# 15. GitHub Actions

La automatización debe dividirse en workflows claros.

## 15.1 CI

Archivo:

```text
.github/workflows/ci.yml
```

Flujo conceptual:

```text
Checkout
   ↓
Setup Python
   ↓
Install dependencies
   ↓
Format check
   ↓
Ruff
   ↓
mypy
   ↓
pytest
   ↓
coverage
   ↓
SonarQube
```

## 15.2 Security

Archivo:

```text
.github/workflows/security.yml
```

Ejecutar:

- CodeQL;
- Semgrep;
- Gitleaks;
- pip-audit;
- Dependency Review cuando corresponda.

## 15.3 Mutation

Archivo:

```text
.github/workflows/mutation.yml
```

Ejecutar:

```text
pytest
→ mutmut
→ validar mutation score
```

## 15.4 Fuzz

Archivo:

```text
.github/workflows/fuzz.yml
```

Ejecutar fuzzing de manera separada para no ralentizar innecesariamente el CI normal.

## 15.5 Docker

Archivo:

```text
.github/workflows/docker.yml
```

Flujo:

```text
Build
→ Hadolint
→ Trivy
```

## 15.6 SBOM

Archivo:

```text
.github/workflows/sbom.yml
```

Flujo:

```text
Build/resolve dependencies
→ Syft
→ Generate SBOM
→ Upload artifact
```

---

# 16. SonarQube

Utilizar **SonarQube** para análisis adicional de calidad.

Debe analizar:

- bugs;
- code smells;
- vulnerabilidades;
- duplicación;
- cobertura;
- mantenibilidad.

Configurar un **Quality Gate**.

El CI debe fallar si el proyecto no cumple las condiciones mínimas definidas.

---

# 17. Git y Pull Requests

## Branch principal

La rama principal será:

```text
main
```

Configurar protección de rama.

Requisitos recomendados:

- Pull Request obligatorio;
- checks obligatorios;
- no permitir push directo;
- revisión antes del merge.

## Pull Request template

Debe incluir:

```text
What changed?

Why?

Tests

Security considerations

Breaking changes

Checklist
```

## CODEOWNERS

Definir responsables para las áreas importantes del repositorio.

---

# 18. Dependencias

Principios:

1. Mantener pocas dependencias.
2. Preferir librerías estándar cuando sean suficientes.
3. Justificar dependencias externas.
4. Mantenerlas actualizadas.
5. Auditar vulnerabilidades.
6. Versionar lockfile.

Cada dependencia importante debería tener una razón explícita.

---

# 19. Documentación

El repositorio debe tener:

## README.md

Debe explicar:

- qué es MarkForge;
- instalación;
- uso;
- ejemplos;
- arquitectura resumida;
- testing;
- seguridad;
- desarrollo local;
- CI;
- licencia.

## docs/architecture.md

Explicar:

- arquitectura;
- componentes;
- flujo;
- decisiones de diseño.

## docs/security.md

Explicar:

- modelo de seguridad;
- sanitización;
- amenazas;
- controles;
- limitaciones.

## docs/testing.md

Explicar:

- unit testing;
- integration testing;
- golden tests;
- property-based testing;
- mutation testing;
- fuzzing;
- benchmarks;
- coverage.

## docs/contributing.md

Explicar:

- entorno;
- instalación;
- comandos;
- commits;
- Pull Requests;
- tests;
- calidad.

## docs/threat-model.md

Documentar:

- activos;
- amenazas;
- vectores;
- mitigaciones;
- riesgos residuales.

---

# 20. ADRs

Utilizar Architecture Decision Records.

Primero:

```text
docs/adr/001-parser-architecture.md
docs/adr/002-ast-design.md
docs/adr/003-html-sanitization.md
```

Cada ADR debe explicar:

- contexto;
- problema;
- opciones consideradas;
- decisión;
- consecuencias.

---

# 21. Configuración central

El archivo:

```text
pyproject.toml
```

debe centralizar, cuando sea apropiado:

- metadata del proyecto;
- dependencias;
- configuración de Ruff;
- configuración de mypy;
- configuración de pytest;
- coverage;
- build;
- CLI entrypoint.

Evitar archivos de configuración innecesarios.

---

# 22. CLI

La CLI debe:

- tener comandos simples;
- mostrar `--help`;
- mostrar `--version`;
- aceptar archivo;
- aceptar stdin;
- permitir output a archivo;
- retornar códigos de salida apropiados;
- mostrar errores útiles;
- no imprimir información sensible.

Ejemplo:

```bash
markforge input.md
```

Salida:

```html
<h1>Hello</h1>
```

Ejemplo:

```bash
markforge input.md --output output.html
```

---

# 23. Manejo de errores

Definir excepciones específicas.

Ejemplos conceptuales:

```python
MarkdownError
LexerError
ParserError
SanitizationError
RenderError
```

Evitar:

```python
except Exception:
    pass
```

Los errores deben:

- ser explícitos;
- ser útiles;
- mantener contexto;
- no filtrar secretos;
- permitir códigos de salida apropiados en CLI.

---

# 24. Principios de diseño

Todo desarrollo debe respetar:

### 24.1 Single Responsibility

Cada componente tiene una responsabilidad clara.

### 24.2 Separation of Concerns

Parsing, seguridad y rendering deben permanecer separados.

### 24.3 Explicit over implicit

Preferir comportamiento explícito.

### 24.4 Secure by default

El comportamiento predeterminado debe ser seguro.

### 24.5 Testability

Las funciones importantes deben poder probarse aisladamente.

### 24.6 Minimal dependencies

No agregar una dependencia si la funcionalidad puede resolverse de manera razonable con la biblioteca estándar.

### 24.7 No premature optimization

Primero claridad y corrección; después optimización basada en benchmarks.

### 24.8 Automation

Todo chequeo repetitivo debe automatizarse.

---

# 25. Definition of Done

Una implementación se considera completa cuando cumple:

## Producto

- [ ] CLI funcional.
- [ ] API Python funcional.
- [ ] Lexer.
- [ ] Parser.
- [ ] AST.
- [ ] Sanitizer.
- [ ] HTML renderer.
- [ ] Manejo de errores.
- [ ] Documentación de uso.

## Testing

- [ ] Unit tests.
- [ ] Integration tests.
- [ ] Golden tests.
- [ ] Property-based tests.
- [ ] Mutation testing.
- [ ] Fuzzing.
- [ ] Benchmarks.
- [ ] Coverage >= 90%.

## Calidad

- [ ] Ruff.
- [ ] mypy.
- [ ] pre-commit.
- [ ] SonarQube.
- [ ] Quality Gate.

## Seguridad

- [ ] CodeQL.
- [ ] Semgrep.
- [ ] Gitleaks.
- [ ] pip-audit.
- [ ] Dependency Review.
- [ ] Dependabot.
- [ ] Security regression tests.
- [ ] Threat model.

## Container

- [ ] Dockerfile.
- [ ] Usuario no-root.
- [ ] Hadolint.
- [ ] Trivy.

## Supply Chain

- [ ] uv.
- [ ] lockfile.
- [ ] SBOM.
- [ ] Syft.
- [ ] CycloneDX o SPDX.
- [ ] Cosign cuando corresponda.

## Repository

- [ ] GitHub Actions.
- [ ] Branch protection.
- [ ] PR template.
- [ ] CODEOWNERS.
- [ ] Issue templates.
- [ ] README.
- [ ] Architecture documentation.
- [ ] Security documentation.
- [ ] Testing documentation.
- [ ] Threat model.
- [ ] ADRs.
- [ ] Contributing guide.
- [ ] LICENSE.

---

# 26. Restricciones importantes para la IA que implemente el sistema

La IA que utilice este documento para construir MarkForge debe respetar las siguientes reglas:

1. **No implementar características fuera del alcance sin justificación.**
2. **No agregar frameworks innecesarios.**
3. **No agregar microservicios.**
4. **No agregar backend web salvo que posteriormente se solicite.**
5. **No agregar frontend salvo que posteriormente se solicite.**
6. **No agregar base de datos.**
7. **No agregar cloud infrastructure sin necesidad.**
8. **No introducir dependencias innecesarias.**
9. **No sacrificar seguridad por simplicidad.**
10. **No sacrificar claridad por abstracciones excesivas.**
11. **Todo código nuevo debe tener tests apropiados.**
12. **Los cambios de arquitectura deben documentarse mediante ADR cuando corresponda.**
13. **Los cambios que afecten seguridad deben documentarse.**
14. **Las herramientas deben tener un propósito concreto.**
15. **El CI debe mantenerse razonablemente rápido.**
16. **Las tareas costosas, como fuzzing y mutation testing, pueden ejecutarse en workflows separados.**
17. **El código debe ser mantenible por un desarrollador humano, no únicamente por la IA.**
18. **Ante una decisión ambigua, priorizar simplicidad, seguridad, testabilidad y mantenibilidad.**

---

# 27. Orden recomendado de implementación

La construcción debe realizarse progresivamente:

```text
1. Project scaffolding
        ↓
2. pyproject.toml + uv
        ↓
3. AST
        ↓
4. Lexer
        ↓
5. Parser
        ↓
6. Renderer
        ↓
7. Sanitizer
        ↓
8. CLI
        ↓
9. Unit tests
        ↓
10. Integration tests
        ↓
11. Golden tests
        ↓
12. Property-based tests
        ↓
13. Security tests
        ↓
14. Ruff + mypy + pre-commit
        ↓
15. SonarQube
        ↓
16. CodeQL + Semgrep + Gitleaks + pip-audit
        ↓
17. Mutation testing
        ↓
18. Fuzzing
        ↓
19. Docker + Hadolint + Trivy
        ↓
20. SBOM
        ↓
21. GitHub Actions
        ↓
22. Documentation
        ↓
23. Final hardening
```

---

# 28. Resultado esperado

El resultado final debe ser un proyecto pequeño, entendible y funcional que pueda utilizarse como demostración de capacidades de ingeniería de software.

El valor principal del proyecto no está en tener una aplicación enorme.

El valor está en demostrar que un desarrollador puede construir un sistema pequeño con:

- arquitectura clara;
- código limpio;
- typing;
- tests;
- cobertura;
- mutation testing;
- property-based testing;
- fuzzing;
- seguridad;
- SAST;
- dependency scanning;
- secret scanning;
- Docker hardening;
- SBOM;
- CI automatizado;
- quality gates;
- documentación;
- decisiones arquitectónicas;
- buenas prácticas de GitHub;
- supply-chain security.

**MarkForge debe ser pequeño en funcionalidad, pero profesional en ingeniería.**
