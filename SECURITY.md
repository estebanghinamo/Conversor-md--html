# Política de seguridad

MarkForge convierte Markdown no confiable en HTML, así que un fallo de seguridad (por ejemplo, una forma de producir XSS) es un problema serio. Gracias por avisar de forma responsable.

## Cómo reportar una vulnerabilidad

**No abras un issue público.** Usa el reporte privado de GitHub:

1. Ve a la pestaña **Security** del repositorio.
2. Pulsa **Report a vulnerability**.
3. Describe el problema e incluye, si puedes:
   - el Markdown de entrada mínimo que lo reproduce y el HTML que obtienes;
   - la versión (`markforge --version`) y el sistema operativo;
   - el impacto que crees que tiene.

Solo el mantenedor y quien reporta ven el informe. Es un proyecto personal y se atiende en la medida de lo posible, sin plazos garantizados. Se agradece que no se divulgue el problema hasta que haya una corrección.

## Versiones con soporte

Solo se corrige la última versión publicada en `main`. El proyecto está en fase 0.x.

## Qué se considera una vulnerabilidad

Por ejemplo: HTML que ejecuta script o carga contenido activo a partir de Markdown, un esquema de URL bloqueado que pasa el sanitizer, un consumo de CPU o memoria desproporcionado con una entrada pequeña, o que la CLI escriba donde no debe.

Los riesgos ya conocidos y aceptados (por ejemplo, que `--output` escribe donde indica quien ejecuta la CLI, o que las imágenes `http(s)` pueden cargarse al abrir el HTML) están en [`docs/security.md`](docs/security.md#riesgos-aceptados) y en el [modelo de amenazas](docs/threat-model.md). Si crees que alguno es más grave de lo documentado, repórtalo igualmente.
