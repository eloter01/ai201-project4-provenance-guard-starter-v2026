import pytest

import config
from scoring import combine_signals


@pytest.mark.parametrize(
    ("model_score", "style_score", "expected"),
    [(0.80, 0.90, 0.85), (0.10, 0.20, 0.15)],
)
def test_combine_signals_averages_aligned_scores(
    model_score: float, style_score: float, expected: float
) -> None:
    assert combine_signals(model_score, style_score) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("model_score", "style_score"),
    [(0.90, 0.50), (0.50, 0.90), (0.80, 0.50), (0.6449, 0.7953)],
)
def test_combine_signals_keeps_unsupported_ai_in_unsure_range(
    model_score: float, style_score: float
) -> None:
    assert combine_signals(model_score, style_score) == 0.50


def test_combine_signals_accepts_both_scores_at_ai_cutoff() -> None:
    assert combine_signals(0.65, 0.65) == 0.65


def test_combine_signals_keeps_average_below_ai_cutoff() -> None:
    assert combine_signals(0.90, 0.30) == pytest.approx(0.60)


@pytest.mark.parametrize("score", [0, 1])
def test_combine_signals_preserves_score_endpoints(score: int) -> None:
    assert combine_signals(score, score) == score


@pytest.mark.parametrize(
    ("score", "error"),
    [
        (None, TypeError),
        ("0.5", TypeError),
        (False, TypeError),
        (True, TypeError),
        (float("nan"), ValueError),
        (float("inf"), ValueError),
        (float("-inf"), ValueError),
        (-0.01, ValueError),
        (1.01, ValueError),
    ],
)
def test_combine_signals_rejects_invalid_scores(
    score: float | str | None, error: type[Exception]
) -> None:
    with pytest.raises(error, match="model_score"):
        combine_signals(score, 0.5)
    with pytest.raises(error, match="style_score"):
        combine_signals(0.5, score)


def test_combine_signals_uses_configured_weights_and_cutoffs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "WEIGHT_MODEL_SIGNAL", 0.75)
    monkeypatch.setattr(config, "WEIGHT_STYLE_SIGNAL", 0.25)
    monkeypatch.setattr(config, "HUMAN_THRESHOLD", 0.20)
    monkeypatch.setattr(config, "AI_THRESHOLD", 0.70)

    assert combine_signals(0.80, 1.00) == pytest.approx(0.85)
    assert combine_signals(0.90, 0.65) == pytest.approx(0.45)
