# Gaps

Huecos reales. No se rellenan copiando el software de vuelo ni inventando bandas,
productos, geo o cuotas.

## 1. Falta de geo-referenciación real en el CubeSat de la UA

No hay efemérides, GPS ni actitud (ADCS) documentadas en el contrato de artefactos
publicados (`*.product` / `events.jsonl`). DARKSKY **no** emite lat/lon para el CubeSat.

Las celdas se tratan como `(row, col)` relativos a la captura:

- `position_frame: scene_relative`
- `georeferenced: false`
- `spatial: None` en la `Scene` UA

Cualquier mapa o “posición” geográfica del CubeSat sería una invención hasta que la
UA publique una fuente confirmada (TLE / GPS / ADCS, o correlación `capture_id` ↔
pasada geo-referenciada en tierra).

NASA Black Marble **sí** trae grilla lat/lon propia del producto. Ese geo no se copia
sobre las celdas UA. El tile `h08v05` de las fixtures CMR es el ejemplo del User Guide,
**no** un AOI de Antofagasta.

## 2. Cómputo a bordo no confirmado para ninguna capa de inteligencia adicional

La Jetson Orin Nano está documentada como asignada al software de vuelo
(adquisición + procesamiento). No hay un segundo computador, ni presupuesto de CPU/NPU
confirmado, para una capa extra de inteligencia a bordo.

Este repo asume **cero** cómputo a bordo adicional:

- no corre en el satélite,
- no reclasifica píxeles crudos,
- no desempaqueta HDF DNB ni `MBRAW1`,
- DARKSKY (y cualquier app futuro) es estrictamente ground-side sobre artefactos ya publicados.

Pendiente UA: confirmar que FIRE/TAILINGS/RAVINE, si alguna vez existen, siguen el
mismo supuesto. Hasta entonces no se implementan.

## 3. Por qué Sentinel-2 L2A está ingerido y testeado pero no se usa en DARKSKY

No existe producto Copernicus equivalente a luces nocturnas VIIRS / NASA Black Marble.
Sentinel-2 L2A es **reflectancia óptica diurna** (colección STAC `sentinel-2-l2a`).

Forzar L2A en DARKSKY como índice de brillo nocturno sería inventar una capacidad que
el emisor no publica. Por eso:

- el adaptador `copernicus_sentinel` **sí** está conectado al DataHub (STAC + OAuth CDSE opcional),
- **sí** tiene tests con `RecordedTransport` y entra al e2e de ingestión,
- DARKSKY lo marca `sentinel_used: false`, cuenta `sentinel_scenes_ignored` y documenta
  la razón en cada reporte.

Usos futuros reales (molde FIRE/TAILINGS/RAVINE) podrían usar S2 L2A para cambio de
cobertura u otra firma óptica **declarada**, nunca como DNB.

Este MVP **no** llama Sentinel Hub `/api/v1/process` (processing units). Solo STAC search
en grabaciones.

## 4. Cuotas reales de Earthdata / Sentinel Hub aún por confirmar

No hay medición de rate-limit, throttling ni processing units con credenciales de
producción de este proyecto.

| Servicio | Qué usa el MVP | Qué falta confirmar |
| --- | --- | --- |
| NASA CMR | `GET /search/granules.umm_json`, Client-Id `ecoaves-orbitalos` | cuotas CMR; si el token es obligatorio en búsqueda vs solo en download HDF |
| NASA LAADS / Earthdata Login | token `EARTHDATA_TOKEN` (nunca en git) | cuotas de download; el MVP **no** desempaqueta SDS de radiancia DNB |
| CDSE STAC | `POST /v1/search` colección `sentinel-2-l2a` | cuotas de la cuenta del proyecto |
| Sentinel Hub Process API | URL aislada; **no** se llama en CI ni en DARKSKY | processing units de la cuenta de producción |

CI nunca pega a APIs reales. Llamadas vivas: `scripts/live_nasa.py` y
`scripts/live_sentinel.py` (fuera de pytest).

## 5. Endpoints que cambiaron (o van a cambiar) durante el desarrollo

Todas las URLs viven en `datahub/adapters/*/endpoints.py`. El Core no las conoce.

### Suomi NPP / VIIRS SNPP — corte 2026-11-01

NASA deja de entregar datos de **Suomi NPP el 1 de noviembre de 2026**. Productos
`VNP46A1`–`VNP46A4` (Black Marble sobre SNPP) se deprioritizan.

Este repo prefiere Collection 2 sobre NOAA-20 / NOAA-21:

- `VJ146A1` (NOAA-20)
- `VJ246A1` (NOAA-21)

VJ246 figura “in development” en la página Black Marble de Earthdata; LAADS ya lista
`VJ246A1`. Fixtures CMR usan esos `ShortName`. No se usa `earthaccess` ni clientes de
terceros: solo CMR `granules.umm_json`.

Earthdata unifica sitios a lo largo de 2026. Si CMR o LAADS cambian de host, se
sobrescribe `ECOAVES_CMR_GRANULES` / el Client-Id sin tocar Core ni DARKSKY.

### Sentinel Hub — reestructuración de rutas, marzo 2026

Sentinel Hub reestructuró rutas en **marzo 2026**. Las URLs de este MVP (CDSE Dataspace) son:

| Uso | Default | Variable |
| --- | --- | --- |
| STAC search | `https://stac.dataspace.copernicus.eu/v1/search` | `ECOAVES_CDSE_STAC_SEARCH` |
| OAuth token | `https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token` | `ECOAVES_CDSE_OAUTH_TOKEN` |
| Process API (no usada en DARKSKY/CI) | `https://sh.dataspace.copernicus.eu/api/v1/process` | `ECOAVES_CDSE_SH_PROCESS` |

No se hardcodean hosts de `sentinel-hub.com` pre-2026 en Core ni en apps.

## Otros huecos (UA / operación)

- **Protocolo de bajada:** GUTS/Pumpkin no confirmado; el drop es un directorio local.
- **Licencia de datos CubeSat:** prototipo de laboratorio, `unpublished-lab-prototype`.
- **HDF / `MBRAW1`:** no se consume. DARKSKY usa `analysis.product` ya calculado.
- **`batch_id`:** lo asigna la ingestión (`--batch`); el artefacto UA no lo trae.
- **Software de vuelo de referencia:** no estuvo montado en este entorno. Contratos
  tomados de la especificación verificada. Cero copia de código, cero imports.
- **Fotometría Black Marble:** MVP `metadata_only`. No se inventa un índice de brillo
  a partir de metadatos CMR.

## Dominios no implementados

FIRE, TAILINGS y RAVINE **no** existen como código. Solo el contrato en
`apps/_template/README.md`. No se empiezan en este MVP.
