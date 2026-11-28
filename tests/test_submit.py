from pathlib import Path

import pytest
from flask.testing import FlaskClient

import config
from app import app

MISSING = object()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FlaskClient:
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "AUDIT_LOG", tmp_path / "audit.jsonl")
    return app.test_client()


def test_submit_returns_json_response(client: FlaskClient) -> None:
    response = client.post(
        "/submit",
        json={
            "text": "The first customer came in for bread.",
            "creator_id": "demo-writer",
        },
    )

    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {
        "content_id": "8e6f17b8-2042-4fa9-9dbf-48bccb4f11ba",
        "guess": "unsure",
        "confidence": 0.5,
        "label": "We are unsure who wrote this text.",
        "model_score": 0.0,
        "style_score": None,
    }


def test_ping_remains_available(client: FlaskClient) -> None:
    response = client.post("/ping", json={"message": "hello"})

    assert response.status_code == 200
    assert response.get_json() == {
        "ok": True,
        "you_sent": "hello",
        "service": "provenance-guard",
    }


@pytest.mark.parametrize(
    "body", ['{"text":', "[]", '"writing"', "42", "true", "null"]
)
def test_submit_rejects_malformed_and_non_object_json(
    client: FlaskClient, body: str
) -> None:
    response = client.post(
        "/submit", data=body, content_type="application/json"
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "invalid_json",
        "message": "Send a valid JSON object.",
    }


@pytest.mark.parametrize("field", ["text", "creator_id"])
@pytest.mark.parametrize(
    "value",
    [pytest.param(MISSING, id="missing"), None, 42, [], "", " \t\n"],
)
def test_submit_rejects_invalid_required_fields(
    client: FlaskClient, field: str, value: object
) -> None:
    payload: dict[str, object] = {
        "text": "The shop opens at eight.",
        "creator_id": "demo-writer",
    }
    if value is MISSING:
        del payload[field]
    else:
        payload[field] = value

    response = client.post("/submit", json=payload)

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "invalid_field",
        "message": f"'{field}' must be a nonblank string.",
    }


@pytest.mark.parametrize(
    ("payload", "creator_id", "reason"),
    [
        ({"creator_id": "demo-writer"}, "demo-writer", "invalid_field"),
        ({"text": "The shop opens at eight."}, "unknown", "invalid_field"),
        ({"creator_id": " "}, "unknown", "invalid_field"),
        ([], "unknown", "invalid_json"),
    ],
)
def test_submit_audits_rejections(
    client: FlaskClient,
    payload: dict[str, str] | list[object],
    creator_id: str,
    reason: str,
) -> None:
    response = client.post("/submit", json=payload)
    log = client.get("/log").get_json()

    assert response.status_code == 400
    assert log["count"] == 1
    entry = log["entries"][0]
    assert entry["creator_id"] == creator_id
    assert entry["event"] == "rejected"
    assert entry["status"] == "rejected"
    assert entry["reason"] == reason


def test_submit_accepts_text_over_400_characters(client: FlaskClient) -> None:
    text = "The first customer came in for bread. " * 12
    response = client.post(
        "/submit", json={"text": text, "creator_id": "demo-writer"}
    )

    assert response.status_code == 200
