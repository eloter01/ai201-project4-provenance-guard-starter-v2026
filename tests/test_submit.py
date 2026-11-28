from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import pytest
from flask.testing import FlaskClient

import config
import detector
import stylometry
from app import app

MISSING = object()
MODEL_SCORE = 0.72


@pytest.fixture(autouse=True)
def stub_model(monkeypatch: pytest.MonkeyPatch) -> Mock:
    model_signal = Mock(return_value=MODEL_SCORE)
    monkeypatch.setattr(detector, "model_signal", model_signal)
    return model_signal


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FlaskClient:
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "AUDIT_LOG", tmp_path / "audit.jsonl")
    return app.test_client()


@pytest.fixture
def stub_style(monkeypatch: pytest.MonkeyPatch) -> Mock:
    style_signal = Mock(return_value=0.88)
    monkeypatch.setattr(stylometry, "style_signal", style_signal)
    return style_signal


@pytest.mark.parametrize(
    ("style_score", "confidence"), [(0.88, 0.80), (0.60, 0.50)]
)
def test_submit_returns_both_signals_and_combined_confidence(
    client: FlaskClient,
    stub_style: Mock,
    style_score: float,
    confidence: float,
) -> None:
    stub_style.return_value = style_score
    response = client.post(
        "/submit",
        json={
            "text": "The first customer came in for bread.",
            "creator_id": "demo-writer",
        },
    )

    assert response.status_code == 200
    assert response.is_json
    body = response.get_json()
    assert UUID(body.pop("content_id")).version == 4
    assert body == {
        "guess": "unsure",
        "confidence": pytest.approx(confidence),
        "label": "We are unsure who wrote this text.",
        "model_score": MODEL_SCORE,
        "style_score": style_score,
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


def test_submit_passes_full_long_text_to_stylometry(
    client: FlaskClient, stub_style: Mock
) -> None:
    text = "  " + "The shop opens at eight. " * 100 + "Last line. "
    response = client.post(
        "/submit", json={"text": text, "creator_id": "demo-writer"}
    )

    assert response.status_code == 200
    stub_style.assert_called_once_with(text)


def test_submit_audit_matches_response_scores(
    client: FlaskClient, stub_model: Mock
) -> None:
    text = "The first customer came in for bread."
    response = client.post(
        "/submit", json={"text": text, "creator_id": "demo-writer"}
    )

    assert response.status_code == 200
    stub_model.assert_called_once_with(text)
    body = response.get_json()

    other = client.post(
        "/submit",
        json={
            "text": "We walk home. They stay here.",
            "creator_id": "another-writer",
        },
    )
    assert other.status_code == 200

    log = client.get("/log").get_json()
    assert log["count"] == 2
    content_id = body["content_id"]
    (entry,) = (
        row for row in log["entries"] if row["content_id"] == content_id
    )
    assert entry["creator_id"] == "demo-writer"
    assert entry["status"] == "decided"
    assert entry["guess"] == body["guess"]
    assert entry["model_score"] == body["model_score"] == MODEL_SCORE
    assert entry["style_score"] == body["style_score"] == 0.50
    assert entry["combined_score"] == body["confidence"]
    assert entry["label"] == body["label"]


def test_submit_assigns_distinct_content_ids(client: FlaskClient) -> None:
    payload = {"text": "The shop opens at eight.", "creator_id": "demo-writer"}
    first = client.post("/submit", json=payload)
    second = client.post("/submit", json=payload)

    assert first.status_code == second.status_code == 200
    assert first.get_json()["content_id"] != second.get_json()["content_id"]


def test_submit_audits_text_too_short(
    client: FlaskClient, stub_model: Mock
) -> None:
    stub_model.side_effect = detector.TextTooShortError()
    response = client.post(
        "/submit", json={"text": "Two tokens", "creator_id": "demo-writer"}
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "text_too_short"
    log = client.get("/log").get_json()
    assert log["count"] == 1
    entry = log["entries"][0]
    assert entry["creator_id"] == "demo-writer"
    assert entry["status"] == "rejected"
    assert entry["reason"] == "text_too_short"


def test_submit_audits_unavailable_detector(
    client: FlaskClient, stub_model: Mock
) -> None:
    stub_model.side_effect = detector.DetectorUnavailable("Model load failed")
    response = client.post(
        "/submit",
        json={"text": "The shop opens at eight.", "creator_id": "demo-writer"},
    )

    assert response.status_code == 503
    assert response.get_json() == {
        "error": "detector_unavailable",
        "message": "The detector is temporarily unavailable.",
    }
    log = client.get("/log").get_json()
    assert log["count"] == 1
    entry = log["entries"][0]
    assert entry["creator_id"] == "demo-writer"
    assert entry["status"] == "rejected"
    assert entry["reason"] == "detector_unavailable"


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {"text": "The shop opens at eight.", "creator_id": "demo-writer"},
            id="decision",
        ),
        pytest.param({"creator_id": "demo-writer"}, id="rejection"),
    ],
)
def test_submit_returns_error_when_audit_write_fails(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    payload: dict[str, str],
) -> None:
    monkeypatch.setattr(config, "AUDIT_LOG", tmp_path)
    response = client.post("/submit", json=payload)

    assert response.status_code == 500
    assert response.get_json() == {
        "error": "audit_unavailable",
        "message": "Could not record the submission.",
    }
