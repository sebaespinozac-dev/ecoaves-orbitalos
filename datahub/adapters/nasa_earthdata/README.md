# Adaptador NASA Earthdata (Black Marble)

## Qué hace
- `discover`: GET CMR `granules.umm_json` con `short_name` (`VJ146A1`, `VJ246A1` por defecto).
- `fetch`: GET del `RelatedUrls` tipo `GET DATA`. Si hay `EARTHDATA_TOKEN`, manda `Authorization: Bearer`.
- Prioriza NOAA-20/21. `VNP46*` (Suomi NPP) solo si se pide explícito: NASA deja de entregar SNPP el **2026-11-01**.

## CI
Cero red. Tests inyectan `RecordedTransport` con JSON en `tests/integration/recordings/`.

## Uso manual (fuera de CI)

1. Crear Earthdata Login: https://urs.earthdata.nasa.gov/
2. Exportar un token EDL (nunca en git):

```bash
export EARTHDATA_TOKEN="..."          # Bearer para CMR/download
# URLs (Earthdata unificado 2026 — se pueden mover):
export ECOAVES_CMR_GRANULES="https://cmr.earthdata.nasa.gov/search/granules.umm_json"
```

3. Correr el script (hace red de verdad):

```bash
python3 scripts/live_nasa.py
```

No se usa `earthaccess` en este MVP: el transporte es stdlib + URLs aisladas en `endpoints.py`, más fácil de mockear y de retargetear cuando Earthdata unifique sitios.

HDF-EOS5 no se desempaqueta aquí (haría falta un parser específico). DARKSKY v0 usa metadatos de gránulo, no radiancia DNB.
