<div align="center">

# Tablas

</div>

| Nombre | Rol | Puntos |
|:-------|:---:|-------:|
| Ana | **Admin** | 10 |
| Luis | `dev` | 7 |
| A \| B | [sitio](https://a.b) | 3 |

Sin fila de alineación no hay tabla:

a | b
c | d

Tabla con filas cortas, largas y sin tuberías externas:

x | y
--|--
1
1 | 2 | 3

Peligros dentro de celdas:

| Entrada | Salida |
|---|---|
| <script>alert(1)</script> | [x](javascript:void) |
| <img src=x onerror=alert(1)> hola | ![i](data:text/html,x) |

> | q | r |
> |---|---|
> | 1 | 2 |

Solo encabezado:

| solo |
|------|
