"""Jobs por lote. Sin tiempo real. El Core no llama APIs: solo adaptadores inyectados."""

from __future__ import annotations

import logging
from typing import Mapping, Sequence

from core.clock import utc_now
from core.registry import AppRegistry
from core.reports import AppReport
from core.storage import Storage
from datahub.adapter import DataHubAdapter, DiscoverCriteria
from datahub.errors import IngestRejection

LOGGER = logging.getLogger("ecoaves_orbitalos.orchestration")


class Orchestrator:
    def __init__(
        self,
        *,
        storage: Storage,
        adapters: Mapping[str, DataHubAdapter],
        registry: AppRegistry,
    ) -> None:
        self.storage = storage
        self.adapters = dict(adapters)
        self.registry = registry

    def ingest(
        self,
        source: str,
        *,
        batch_id: str,
        criteria: DiscoverCriteria | None = None,
    ) -> dict[str, int]:
        adapter = self._adapter(source)
        criteria = criteria or DiscoverCriteria()
        accepted = 0
        rejected = 0
        for ref in adapter.discover(criteria):
            try:
                payload = adapter.fetch(ref)
                scene = adapter.normalize(payload)
                self.storage.save_scene(scene, batch_id=batch_id)
                accepted += 1
                LOGGER.info(
                    "ACEPTADO source=%s granule=%s product=%s",
                    scene.provenance.source,
                    scene.provenance.granule_id,
                    scene.provenance.product_id,
                )
            except IngestRejection as exc:
                rejected += 1
                self.storage.save_rejection(
                    batch_id=batch_id,
                    source=source,
                    uri=ref.uri,
                    reason=exc.reason,
                    detail=str(exc),
                    rejected_at_utc=utc_now(),
                )
                LOGGER.error("RECHAZO source=%s uri=%s reason=%s detail=%s", source, ref.uri, exc.reason, exc)
        return {"accepted": accepted, "rejected": rejected}

    def ingest_sources(
        self,
        sources: Sequence[str],
        *,
        batch_id: str,
        criteria_by_source: Mapping[str, DiscoverCriteria] | None = None,
    ) -> dict[str, dict[str, int]]:
        criteria_by_source = criteria_by_source or {}
        return {
            source: self.ingest(
                source,
                batch_id=batch_id,
                criteria=criteria_by_source.get(source),
            )
            for source in sources
        }

    def process_app(self, app_name: str, *, batch_id: str) -> AppReport:
        app = self.registry.get(app_name)
        scenes = self.storage.scenes_for_batch(batch_id, sources=app.consumes_sources)
        report = app.process(scenes, batch_id=batch_id)
        self.storage.save_report(report)
        return report

    def _adapter(self, source: str) -> DataHubAdapter:
        try:
            return self.adapters[source]
        except KeyError as exc:
            known = ", ".join(sorted(self.adapters)) or "(ninguno)"
            raise KeyError(f"fuente no conectada {source!r}; conectadas: {known}") from exc
