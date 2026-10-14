"""Envoltorio de página HTML completa para la CLI (`--standalone`).

Funciona sobre el HTML que ya produjo el renderer: no parsea ni decide seguridad.
El único dato variable propio es el título, que se escapa. La página lleva una
política CSP sin scripts como defensa en profundidad.
"""

from html import escape

DEFAULT_TITLE = "MarkForge"

# Sin scripts, formularios ni conexiones; solo estilos propios e imágenes http(s)/relativas.
# base-uri y form-action no heredan de default-src, por eso se fijan aparte.
_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' http: https:; "
    "base-uri 'none'; form-action 'none'"
)

_STYLE = """
:root { color-scheme: light dark; }
body {
  max-width: 46rem; margin: 2.5rem auto; padding: 0 1rem;
  font: 1rem/1.65 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  color: #1f2328; background: #fff;
}
h1, h2, h3, h4, h5, h6 { line-height: 1.25; margin: 1.8em 0 .6em; }
h1, h2 { padding-bottom: .3em; border-bottom: 1px solid #d0d7de; }
a { color: #0969da; }
img { max-width: 100%; height: auto; }
code, pre { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: .9em; }
code { background: #eff1f3; padding: .15em .35em; border-radius: 4px; }
pre { background: #f6f8fa; padding: 1rem; overflow-x: auto; border-radius: 6px; }
pre code { background: none; padding: 0; }
blockquote { margin: 1em 0; padding: 0 1em; color: #59636e; border-left: .25em solid #d0d7de; }
table {
  border-collapse: collapse; display: block; max-width: 100%; overflow-x: auto; margin: 1em 0;
}
th, td { border: 1px solid #d0d7de; padding: .4em .8em; }
th { background: #f6f8fa; font-weight: 600; }
tbody tr:nth-child(even) { background: #f6f8fa; }
hr { border: 0; border-top: 1px solid #d0d7de; margin: 2em 0; }
@media (prefers-color-scheme: dark) {
  body { color: #e6edf3; background: #0d1117; }
  h1, h2, hr, blockquote, th, td { border-color: #30363d; }
  th, tbody tr:nth-child(even) { background: #161b22; }
  a { color: #58a6ff; }
  code { background: #262c36; }
  pre { background: #161b22; }
  blockquote { color: #9198a1; }
}
"""


def wrap_page(fragment: str, title: str = DEFAULT_TITLE) -> str:
    """Devuelve una página HTML completa con el fragmento en el `<body>`."""
    return (
        "<!doctype html>\n"
        '<html lang="es">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta http-equiv="Content-Security-Policy" content="{_CSP}">\n'
        f"<title>{escape(title)}</title>\n"
        f"<style>{_STYLE}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{fragment}"
        "</body>\n"
        "</html>\n"
    )
