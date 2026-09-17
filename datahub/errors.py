"""Errores de ingestión. Un contract/schema desconocido nunca se traga en silencio."""

from __future__ import annotations


class IngestRejection(Exception):
    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        super().__init__(message)


class RejectionReason:
    UNRECOGNIZED_CONTRACT = "unrecognized_contract"
    SCHEMA_MISMATCH = "schema_mismatch"
    UNRECOGNIZED_KIND = "unrecognized_kind"
    INVALID_FILENAME = "invalid_filename"
    INVALID_EVENT = "invalid_event"
    HTTP_UNEXPECTED = "http_unexpected"
    AUTH_MISSING = "auth_missing"
    PRODUCT_NOT_ALLOWED = "product_not_allowed"
    EMPTY_CATALOG = "empty_catalog"
