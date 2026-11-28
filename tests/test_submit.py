from app import app


def test_submit_returns_json_response() -> None:
    response = app.test_client().post(
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


def test_ping_remains_available() -> None:
    response = app.test_client().post("/ping", json={"message": "hello"})

    assert response.status_code == 200
    assert response.get_json() == {
        "ok": True,
        "you_sent": "hello",
        "service": "provenance-guard",
    }
