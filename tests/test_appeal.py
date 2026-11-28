from pathlib import Path
from unittest.mock import Mock

import pytest
from flask.testing import FlaskClient

import audit
import config
from app import app

CONTENT_ID = "text-1"
CREATOR_ID = "writer-1"
REASONING = "I wrote this from my notes."
APPEAL = {"content_id": CONTENT_ID, "reasoning": REASONING}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FlaskClient:
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "AUDIT_LOG", tmp_path / "audit.jsonl")
    return app.test_client()


def test_appeal_preserves_original_decision(client: FlaskClient) -> None:
    decision = audit.log_decision(CONTENT_ID, CREATOR_ID, guess="ai")
    response = client.post(
        "/appeal", json={**APPEAL, "creator_id": "another-writer"}
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "content_id": CONTENT_ID,
        "status": "under_review",
    }
    original, appeal = client.get("/log").get_json()["entries"]
    assert original == decision
    assert original["status"] == "decided"
    assert isinstance(appeal.pop("timestamp"), str)
    assert appeal == {
        "content_id": CONTENT_ID,
        "creator_id": CREATOR_ID,
        "event": "appeal",
        "status": "under_review",
        "reasoning": REASONING,
    }


def test_appeal_exact_retry_returns_same_confirmation(
    client: FlaskClient,
) -> None:
    audit.log_decision(CONTENT_ID, CREATOR_ID)
    first = client.post("/appeal", json=APPEAL)
    retry = client.post("/appeal", json=APPEAL)

    assert first.status_code == retry.status_code == 200
    assert first.get_json() == retry.get_json()
    statuses = [entry["status"] for entry in audit.entries_for(CONTENT_ID)]
    assert statuses == ["decided", "under_review"]


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ('{"reasoning":', None),
        ("[]", None),
        ('"reasoning"', None),
        ("null", None),
        ('{"reasoning":"I wrote this."}', "content_id"),
        ('{"content_id":null,"reasoning":"I wrote this."}', "content_id"),
        ('{"content_id":42,"reasoning":"I wrote this."}', "content_id"),
        ('{"content_id":"","reasoning":"I wrote this."}', "content_id"),
        ('{"content_id":" \\t","reasoning":"I wrote this."}', "content_id"),
        ('{"content_id":"text-1"}', "reasoning"),
        ('{"content_id":"text-1","reasoning":null}', "reasoning"),
        ('{"content_id":"text-1","reasoning":[]}', "reasoning"),
        ('{"content_id":"text-1","reasoning":""}', "reasoning"),
        ('{"content_id":"text-1","reasoning":" \\n"}', "reasoning"),
    ],
)
def test_appeal_rejects_and_audits_invalid_input(
    client: FlaskClient, body: str, field: str | None
) -> None:
    response = client.post(
        "/appeal", data=body, content_type="application/json"
    )
    error = "invalid_field" if field else "invalid_json"
    message = (
        f"'{field}' must be a nonblank string."
        if field
        else "Send a valid JSON object."
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": error, "message": message}
    (entry,) = audit.read_entries()
    assert entry["event"] == entry["status"] == "rejected"
    assert entry["route"] == "/appeal"
    assert entry["reason"] == error
    if field == "reasoning":
        assert entry["content_id"] == CONTENT_ID


def test_appeal_audits_unknown_id_and_still_returns_404_on_retry(
    client: FlaskClient,
) -> None:
    for _ in range(2):
        response = client.post("/appeal", json=APPEAL)

        assert response.status_code == 404
        assert response.get_json() == {
            "error": "content_not_found",
            "message": "No decision was found for this content ID.",
        }

    entries = audit.entries_for(CONTENT_ID)
    assert len(entries) == 2
    for entry in entries:
        assert entry["event"] == entry["status"] == "rejected"
        assert entry["route"] == "/appeal"
        assert entry["reason"] == "content_not_found"


@pytest.mark.parametrize(
    "audit_operation", ["entries_for", "log_appeal", "log_rejection"]
)
def test_appeal_returns_error_on_audit_failure(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
    audit_operation: str,
) -> None:
    audit.log_decision(CONTENT_ID, CREATOR_ID)
    fail = Mock(side_effect=OSError("Audit file is inaccessible"))
    monkeypatch.setattr(audit, audit_operation, fail)
    payload = {} if audit_operation == "log_rejection" else APPEAL

    response = client.post("/appeal", json=payload)

    assert response.status_code == 500
    assert response.get_json() == {
        "error": "audit_unavailable",
        "message": "Could not record the appeal.",
    }
    fail.assert_called_once()
