# ECOAVES OrbitalOS

DataHub terrestre + **visor satelital** con imágenes reales de NASA Worldview y Copernicus Sentinel-2.

## Estado

- Core + DataHub + DARKSKY (Hito 6)
- Visor web profesional (Hito 7): geocoding, snapshots NASA, galería Sentinel-2
- Sin pygame / Matrix
- CI sin red

## Visor satelital

```bash
cd ecoaves-orbitalos
pip install ".[server]"
python3 server.py
```

Abre http://localhost:8000

1. Escribe un lugar (`Antofagasta`) o coordenadas (`-23.6509, -70.3975`)
2. El mapa marca la zona (±1°)
3. Panel derecho: imagen NASA Worldview (color verdadero / luces nocturnas / MODIS / IMERG)
4. Panel izquierdo: módulos DARKSKY / FIRE / TAILINGS / RAVINE (overlays en el mapa)
5. Abajo: thumbnails Sentinel-2 de los últimos 7 días (clic para ampliar)

No requiere API keys para el flujo básico. Opcional: `FIRMS_MAP_KEY` para API Area NRT de FIRMS (sin key se usa CSV público regional 24h).

Variables opcionales:

```bash
ECOAVES_HOST=0.0.0.0
ECOAVES_PORT=8000
FIRMS_MAP_KEY=
```

### Módulos

| Módulo | Fuente | En el mapa |
| --- | --- | --- |
| DARKSKY | VIIRS Day/Night Band (Worldview) | Overlay semitransparente |
| FIRE | NASA FIRMS VIIRS | Marcadores de focos |
| TAILINGS | Sentinel-2 STAC | Comparar antes/después |
| RAVINE | IMERG Precipitation Rate | Overlay precipitación |
## CLI offline (DARKSKY)

```bash
python3 -m pip install pytest
python3 -m pytest
python3 cli.py run --drop ./var/drop --db ./var/orbitalos.sqlite3 --batch DEMO --out ./var/reports
```

## Fuentes DataHub

| Adaptador | Entrada | Uso |
| --- | --- | --- |
| `nasa_earthdata` | CMR Black Marble | DARKSKY |
| `cubesat_ua` | drop local | DARKSKY |
| `copernicus_sentinel` | STAC S2 L2A | DataHub (no DARKSKY) |
| `datahub/imagery.py` | Worldview + STAC + Nominatim | Visor web |

## Dependencias

- Runtime CLI/Core: stdlib
- Tests: `pytest`
- Servidor: `pip install ".[server]"` → fastapi, uvicorn, httpx

## Aislamiento UA

Ningún import, subproceso ni ruta al software de vuelo. Solo el drop publicado.

## Documentación

`docs/architecture.md`, `docs/gaps.md`, `apps/_template/README.md`.
