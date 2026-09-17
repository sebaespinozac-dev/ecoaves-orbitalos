"""Registro de apps. Core no conoce contaminación lumínica ni productos satelitales."""

from __future__ import annotations

from typing import Protocol, Sequence

from core.models import Scene
from core.reports import AppReport


class AppProcessor(Protocol):
    name: str
    consumes_sources: frozenset[str]
    produces: frozenset[str]

    def process(self, scenes: Sequence[Scene], *, batch_id: str) -> AppReport:
        """Recibe Scenes ya normalizadas. No abre drops ni APIs."""


class AppRegistry:
    def __init__(self) -> None:
        self._apps: dict[str, AppProcessor] = {}

    def register(self, processor: AppProcessor) -> None:
        name = processor.name
        if not name or name.startswith("_"):
            raise ValueError(f"nombre de app inválido: {name!r}")
        if name in self._apps:
            raise ValueError(f"app ya registrada: {name}")
        if not processor.consumes_sources:
            raise ValueError(f"{name} debe declarar consumes_sources")
        self._apps[name] = processor

    def get(self, name: str) -> AppProcessor:
        try:
            return self._apps[name]
        except KeyError as exc:
            known = ", ".join(sorted(self._apps)) or "(ninguna)"
            raise KeyError(f"app desconocida {name!r}; registradas: {known}") from exc

    def names(self) -> list[str]:
        return sorted(self._apps)
