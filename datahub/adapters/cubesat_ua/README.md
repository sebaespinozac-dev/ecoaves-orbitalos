# Adaptador cubesat_ua

Lee un directorio drop local con artefactos ya publicados:

- `{capture_id}.{kind}.product`
- `events.jsonl`

No abre `raw/`, `work/` ni el catálogo SQLite del software de vuelo. Un `contract` distinto de `ua.blue_proxy.analysis.v1` se rechaza con error explícito. No hay geo-referencia.
