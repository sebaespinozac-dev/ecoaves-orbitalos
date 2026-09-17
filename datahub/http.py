"""Transporte HTTP inyectable. Las URLs nunca viven en Core.

LiveHttpTransport usa urllib y SOLO debe usarse fuera de CI (scripts manuales).
Los tests inyectan RecordedTransport: cualquier URL no grabada falla en duro.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class HttpResponse:
    status: int
    url: str
    headers: Mapping[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))

    def text(self) -> str:
        return self.body.decode("utf-8")


class HttpTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, str]] = None,
        json_body: Any = None,
        form: Optional[Mapping[str, str]] = None,
    ) -> HttpResponse:
        ...


class UnexpectedHttpError(RuntimeError):
    """El test tocó una URL que no está en las grabaciones — no hay red de respaldo."""


class RecordedTransport:
    """Respuestas grabadas. Cero red."""

    def __init__(self, recordings: Mapping[tuple[str, str], HttpResponse]) -> None:
        self._recordings = dict(recordings)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, str]] = None,
        json_body: Any = None,
        form: Optional[Mapping[str, str]] = None,
    ) -> HttpResponse:
        extra = ""
        if params and params.get("short_name"):
            extra = f"|short_name={params['short_name']}"
        elif json_body and isinstance(json_body, dict) and json_body.get("collections"):
            extra = f"|collections={json_body['collections'][0]}"
        key = (method.upper(), url + extra)
        if key in self._recordings:
            return self._recordings[key]
        full = url
        if params:
            full = f"{url}?{urlencode(params)}"
        if (method.upper(), full) in self._recordings:
            return self._recordings[(method.upper(), full)]
        raise UnexpectedHttpError(
            f"CI no permite red; no hay grabación para {method} {url}{extra or full}"
        )


class LiveHttpTransport:
    """Cliente stdlib. No importar desde tests."""

    def __init__(self, timeout_s: int = 60) -> None:
        self.timeout_s = timeout_s

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, str]] = None,
        json_body: Any = None,
        form: Optional[Mapping[str, str]] = None,
        timeout_s: Optional[int] = None,
    ) -> HttpResponse:
        full = url
        if params:
            full = f"{url}?{urlencode(params)}"
        hdrs = {"User-Agent": "ecoaves-orbitalos/0.1 (ground datahub; no flight software)"}
        if headers:
            hdrs.update(headers)
        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        elif form is not None:
            data = urlencode(form).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
        request = Request(full, data=data, headers=hdrs, method=method.upper())
        try:
            with urlopen(request, timeout=timeout_s or self.timeout_s) as resp:
                body = resp.read()
                status = getattr(resp, "status", 200)
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
                return HttpResponse(status=status, url=full, headers=resp_headers, body=body)
        except HTTPError as exc:
            body = exc.read() if exc.fp else b""
            raise RuntimeError(f"HTTP {exc.code} {full}: {body[:200]!r}") from exc
        except URLError as exc:
            raise RuntimeError(f"red falló para {full}: {exc}") from exc
