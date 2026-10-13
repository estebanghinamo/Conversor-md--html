# ADR-002: Diseño del AST

**Estado:** Aceptado · **Fecha:** 2026-10-13

## Contexto
El AST es el contrato entre parser, sanitizer y renderer (spec §6.4). Debe ser pequeño, tipado y sin dependencias.

## Problema
Elegir cómo representar los nodos y cómo recorrerlos sin acoplar etapas.

## Opciones consideradas
1. Dataclasses inmutables (`frozen=True, slots=True`) y uniones de tipos (`Inline`, `Block`).
2. Jerarquía de clases con patrón visitor.

## Decisión
Opción 1. Los hijos son `tuple` (inmutables y hashables). Los nodos guardan datos crudos: no validan seguridad (solo el nivel de `Heading`, que es invariante estructural). El sanitizer devuelve un AST nuevo; el renderer despacha por tipo con `match`.

## Consecuencias
- Sin dependencias y con mypy estricto; `match` exhaustivo sobre las uniones.
- Cada nodo nuevo exige actualizar sanitizer y renderer.
- Un visitor puede añadirse luego sin cambiar los nodos.
