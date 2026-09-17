# ECOAVES OrbitalOS

DataHub terrestre. Tres fuentes conectadas al Core; DARKSKY usa NASA Black Marble (primaria) y CubeSat UA (secundaria).

## Estado

MVP Core + DataHub + DARKSKY. Visor satelital web (NASA Worldview + Copernicus STAC) en desarrollo.

## Uso offline (grabaciones HTTP + drop sintético)

```bash
cd ecoaves-orbitalos
python3 -m pip install pytest
python3 -m pytest
python3 cli.py run --drop ./var/drop --db ./var/orbitalos.sqlite3 --batch DEMO --out ./var/reports
```

## Fuentes

| Adaptador | Entrada | DARKSKY |
| --- | --- | --- |
| `nasa_earthdata` | CMR `granules.umm_json`, fetch GET DATA. Prefiere `VJ146A1`/`VJ246A1` | primaria |
| `cubesat_ua` | directorio drop `{id}.{kind}.product` + `events.jsonl` | secundaria, sin geo |
| `copernicus_sentinel` | STAC `sentinel-2-l2a`, OAuth CDSE opcional | no (no hay producto de luces nocturnas) |

Credenciales: `EARTHDATA_TOKEN`, `CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET` (ver `.env.example`). Nunca en git.

## Dependencias

Runtime: stdlib. Tests: pytest. Servidor web: `pip install ".[server]"`.

## Aislamiento UA

Ningún import, subproceso ni ruta al software de vuelo. Solo el drop publicado.

## Documentación

`docs/architecture.md`, `docs/gaps.md`, `apps/_template/README.md`.
