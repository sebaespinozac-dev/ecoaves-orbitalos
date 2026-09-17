# Contrato de un app futuro (molde FIRE / TAILINGS / RAVINE)

Esta carpeta es **solo el molde**. No hay paquete Python aquí. FIRE, TAILINGS y
RAVINE **no** están implementados y **no** deben implementarse en el MVP
(Core + DataHub + DARKSKY).

El único app registrado es `apps/darksky`. Un app nuevo se engancha al Core
**después** de la ingestión. El Core no conoce contaminación lumínica, fuego,
relaves ni quebradas: el app declara qué fuentes consume y qué produce.

## Qué debe declarar

Cumple `core.registry.AppProcessor`:

| Campo | Significado |
| --- | --- |
| `name` | Identificador estable en minúsculas (`fire`, `tailings`, `ravine`, …). Sin prefijo `_`. |
| `consumes_sources` | Subconjunto no vacío de `nasa_earthdata`, `copernicus_sentinel`, `cubesat_ua`. |
| `produces` | Productos de *este* repositorio, versionados (ej. `fire.batch_report`). |

## Qué debe implementar

```text
process(scenes, *, batch_id) -> AppReport
```

- Recibe `Scene` ya normalizadas por el DataHub, cada una con `Provenance` completa.
  No abre el drop, no llama CMR/STAC, no lee `raw/` ni `catalog.sqlite3` de vuelo.
- Cada cifra del reporte se cita con `scene.cite(...)` (copia `Provenance`). Nada
  huérfano: si no hay procedencia, no se publica el número.
- `schema_version` propio, p. ej. `ecoaves_orbitalos.<app>.report.v1`.
- Resumen legible en `AppReport.summary_text`.
- Rechaza o reporta explícitamente escenas que no traen las observaciones que necesita.
  No rellena huecos con valores inventados.

## Qué no debe hacer

- Importar, ejecutar o leer el árbol del software de vuelo de la UA.
- Asumir cómputo a bordo extra (la Jetson Orin Nano no está confirmada para una
  capa de inteligencia adicional). Todo es ground-side.
- Asumir protocolo de bajada (GUTS/Pumpkin u otro): la entrada ya llegó al DataHub.
- Inventar bandas, productos o geo-referencia que la fuente no declare.
- Tratar celdas CubeSat como lat/lon. Hasta que existan efemérides: `scene_relative`.
- Usar Sentinel-2 L2A como luces nocturnas / DNB / Black Marble. L2A es óptico diurno.
  Un app que lo consuma debe justificar el producto real (p. ej. cambio de cobertura,
  NDVI, índice de quemado **si** las bandas están en la `Scene`), no un proxy de DNB.
- Pegar a APIs reales desde tests. CI usa `RecordedTransport` y simuladores de
  *este* repo.

## Fuentes disponibles (hoy)

| `source` | Qué hay en `Scene` | Geo |
| --- | --- | --- |
| `nasa_earthdata` | metadatos Black Marble (`VJ146A1`/`VJ246A1` preferidos; SNPP/`VNP46` sunset 2026-11-01). Sin unpack HDF DNB en este MVP. | grilla del producto NASA |
| `copernicus_sentinel` | ítem STAC `sentinel-2-l2a` (metadatos). Process API de Sentinel Hub **no** se llama en el MVP. | bbox del ítem STAC |
| `cubesat_ua` | `ua.blue_proxy.analysis.v1` ya calculado + PPM grid/heatmap si existen | **no** — `scene_relative` |

## Cómo engancharlo (cuando deje de ser molde)

1. Crear `apps/<nombre>/` con un procesador que cumpla `AppProcessor`.
2. Registrar la instancia en `apps.default_registry` (`apps/__init__.py`).
3. Cubrir con tests sintéticos (y e2e con grabaciones si usa NASA/Sentinel).
4. Documentar en `docs/gaps.md` cualquier supuesto que la fuente aún no confirme.

No copiar software de vuelo. No empezar FIRE, TAILINGS ni RAVINE hasta que este
contrato y las fuentes que declare estén confirmados.
