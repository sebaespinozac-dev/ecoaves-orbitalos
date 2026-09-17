"""Hito 0/conexión: red solo en datahub/http.py (LiveHttpTransport). Tests no lo instancian."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

NETWORK_OK = {ROOT / "datahub" / "http.py"}
# httpx solo vía dependencia opcional [server] / TestClient; no en el núcleo offline.
FORBIDDEN_EVERYWHERE = {"requests", "earthaccess", "aiohttp", "subprocess"}
FORBIDDEN_EXCEPT_HTTP = {"socket", "ssl", "http", "urllib"}
# LiveHttpTransport solo en datahub/http.py y server.py (visor live).
LIVE_TRANSPORT_OK = {ROOT / "datahub" / "http.py", ROOT / "server.py"}


def _production_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*.py"):
        if "tests" in path.parts or ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


def test_no_third_party_http_or_subprocess() -> None:
    offenders: list[str] = []
    for path in _production_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            for name in names:
                root_mod = name.split(".")[0]
                if root_mod in FORBIDDEN_EVERYWHERE or name in FORBIDDEN_EVERYWHERE:
                    offenders.append(f"{path.relative_to(ROOT)}:{name}")
                if root_mod in FORBIDDEN_EXCEPT_HTTP and path.resolve() not in NETWORK_OK:
                    offenders.append(f"{path.relative_to(ROOT)}:{name}")
    assert offenders == []


def test_live_transport_not_imported_by_cli_default() -> None:
    cli = (ROOT / "cli.py").read_text(encoding="utf-8")
    assert "LiveHttpTransport" not in cli
    # server.py sí usa LiveHttpTransport (visor con APIs públicas).
    assert "LiveHttpTransport" in (ROOT / "server.py").read_text(encoding="utf-8")
    for path in LIVE_TRANSPORT_OK:
        assert path.exists()
