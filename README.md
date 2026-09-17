# ECOAVES OrbitalOS

DataHub terrestre. Tres fuentes **conectadas** al Core; DARKSKY usa NASA Black Marble (primaria) y CubeSat UA (secundaria). Sentinel está cableado y testeado, **no** entra en DARKSKY.

## Estado

MVP **cerrado** (Core + DataHub + DARKSKY): contratos, tres fuentes conectadas, DARKSKY v0, documentación Hito 6 y molde `apps/_template`. FIRE / TAILINGS / RAVINE **no** implementados. CI sin red.

## Uso offline (grabaciones HTTP + drop sintético)

```bash
cd ecoaves-orbitalos
python3 -m pip install pytest pygame
python3 -m pytest
python3 cli.py run --drop ./var/drop --db ./var/orbitalos.sqlite3 --batch DEMO --out ./var/reports
python3 cli.py run --drop ./var/drop --db ./var/orbitalos.sqlite3 --batch DEMO --out ./var/reports --pygame
python3 matrix.py --report ./var/reports/DEMO.darksky.json   # HUD 8x6 con celdas reales
MATRIX_SECONDS=4 python3 matrix.py --report ./var/reports/DEMO.darksky.json
python3 matrix.py              # Pygame 1280x720. F = fullscreen, ESC = salir

```

## Fuentes

| Adaptador | Entrada | DARKSKY |
| --- | --- | --- |
| `nasa_earthdata` | CMR `granules.umm_json`, fetch GET DATA. Prefiere `VJ146A1`/`VJ246A1` (SNPP/`VNP46` sunset 2026-11-01) | primaria |
| `cubesat_ua` | directorio drop `{id}.{kind}.product` + `events.jsonl` | secundaria, sin geo |
| `copernicus_sentinel` | STAC `sentinel-2-l2a`, OAuth CDSE opcional | no (no hay producto de luces nocturnas) |

URLs aisladas en `datahub/adapters/*/endpoints.py`. Credenciales: `EARTHDATA_TOKEN`, `CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET` (ver `.env.example`). Nunca en git.

Llamadas reales (no CI): `python3 scripts/live_nasa.py`, `python3 scripts/live_sentinel.py`.

## Dependencias

Runtime: stdlib. Tests: pytest. Visual Matrix: `pygame` (`pip install pygame` o `.[matrix]`).

## Aislamiento UA

Ningún import, subproceso ni ruta al software de vuelo. Solo el drop publicado.

## Documentación

`docs/architecture.md`, `docs/gaps.md`, `apps/_template/README.md`.
