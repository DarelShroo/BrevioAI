from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.brevio.constants.constants import Constants
from core.brevio_api.__main__ import app


@pytest.fixture()
def example_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_root = tmp_path / "data"
    root = data_root / "example"
    entry = root / "6aa98ec497a3c29b27d89204" / "0"
    entry.mkdir(parents=True)
    (entry / "summary.md").write_text(
        "# Demo\n\n- **End-of-Chapter Tools**: sample\n", encoding="utf-8"
    )
    (entry / "sample.pdf").write_bytes(b"%PDF-1.4 demo")
    manifest = {
        "version": 1,
        "default_slug": "summary_d89204",
        "entries": [
            {
                "id": "6aa98ec497a3c29b27d89204",
                "slug": "summary_d89204",
                "title": "Principles of Marketing",
                "document_name": "sample.pdf",
                "category": "Marketing",
                "style": "Informe",
                "type": "Documentos",
                "model": "qwen3:14b",
                "results": 1,
                "created_label": "15 sept 2026, 18:30",
                "summary_file": "summary.md",
                "pdf_file": "sample.pdf",
                "default": True,
                "highlights": [
                    {
                        "summary_match": "End-of-Chapter Tools",
                        "pdf_ratio": 0.18,
                        "summary_ratio": 0.12,
                    }
                ],
            }
        ],
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(Constants, "DESTINATION_FOLDER", str(data_root))
    return root


def test_list_and_fetch_example_without_auth(example_tree: Path) -> None:
    client = TestClient(app)
    listed = client.get("/examples")
    assert listed.status_code == 200
    body = listed.json()
    assert body["default_slug"] == "summary_d89204"
    assert body["entries"][0]["slug"] == "summary_d89204"

    detail = client.get("/examples/summary_d89204")
    assert detail.status_code == 200
    assert detail.json()["id"] == "6aa98ec497a3c29b27d89204"

    summary = client.get("/examples/d89204/summary")
    assert summary.status_code == 200
    assert "End-of-Chapter Tools" in summary.text

    pdf = client.get("/examples/summary_d89204/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")
    assert "x-frame-options" not in {k.lower() for k in pdf.headers.keys()}


def test_example_path_traversal_rejected(example_tree: Path) -> None:
    client = TestClient(app)
    assert client.get("/examples/../etc/passwd").status_code == 404
