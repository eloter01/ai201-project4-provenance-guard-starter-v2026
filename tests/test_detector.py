import math
import sys
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import detector


def test_detector_requires_three_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    two_tokens = SimpleNamespace(shape=(1, 2))
    three_tokens = SimpleNamespace(shape=(1, 3))
    tokenizer = Mock(
        side_effect=[{"input_ids": two_tokens}, {"input_ids": three_tokens}]
    )
    loss = Mock()
    loss.item.return_value = 1.0
    model = Mock(return_value=SimpleNamespace(loss=loss))
    monkeypatch.setattr(
        detector, "_load", Mock(return_value=(model, tokenizer))
    )
    monkeypatch.setitem(
        sys.modules, "torch", SimpleNamespace(no_grad=nullcontext)
    )

    with pytest.raises(detector.TextTooShortError):
        detector.perplexity("Two tokens")
    model.assert_not_called()

    assert detector.perplexity("Three model tokens") == pytest.approx(math.e)
    model.assert_called_once_with(three_tokens, labels=three_tokens)


def test_detector_reports_missing_torch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "torch", None)

    with pytest.raises(detector.DetectorUnavailable):
        detector.model_signal("Three model tokens")
