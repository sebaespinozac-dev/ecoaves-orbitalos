# Adaptador Copernicus Sentinel

## Qué hace
- `discover`: POST STAC `sentinel-2-l2a` (catálogo CDSE).
- `fetch`: GET del item STAC. Si hay `CDSE_CLIENT_ID` / `CDSE_CLIENT_SECRET`, pide token OAuth y lo adjunta.
- **No** hay producto Sentinel de luces nocturnas. DARKSKY no usa este adaptador.

## CI
`RecordedTransport` + JSON en `tests/integration/recordings/`. Cero red.

## Uso manual (fuera de CI)

```bash
export CDSE_CLIENT_ID="..."
export CDSE_CLIENT_SECRET="..."
# Rutas SH se movieron en marzo 2026; no las copies a Core:
export ECOAVES_CDSE_STAC_SEARCH="https://stac.dataspace.copernicus.eu/v1/search"
export ECOAVES_CDSE_OAUTH_TOKEN="https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
python3 scripts/live_sentinel.py
```

Sentinel Hub cobra processing units. Este MVP no llama `/api/v1/process` desde DARKSKY ni desde el pipeline de tests.
