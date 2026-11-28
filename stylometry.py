"""Measure sentence length and vocabulary variety as a style signal."""

import re
import statistics
import sys

import config


def _validate_text(text: str) -> None:
    if not isinstance(text, str):
        raise TypeError("Text must be a string.")
    if not text.strip():
        raise ValueError("Text must not be blank.")


def sentences(text: str) -> list[str]:
    """Split text at sentence-ending punctuation followed by whitespace."""
    _validate_text(text)
    return re.split(r"(?<=[.!?])\s+", text.strip())


def words(text: str) -> list[str]:
    """Split text into lowercase words, keeping apostrophes within words."""
    _validate_text(text)
    return re.findall(r"[^\W_]+(?:'[^\W_]+)*", text.lower().replace("’", "'"))


def sentence_length_spread(text: str) -> float | None:
    """Return sample standard deviation divided by mean sentence length.

    Args:
        text: Passage to measure.

    Returns:
        The spread in word counts, or None with fewer than two
        word-bearing sentences.
    """
    lengths = []
    for sentence in sentences(text):
        length = len(words(sentence))
        if length:
            lengths.append(length)

    if len(lengths) < 2:
        return None
    return statistics.stdev(lengths) / statistics.mean(lengths)


def type_token_ratio(text: str) -> float | None:
    """Return the average unique-word ratio across rolling 20-word windows.

    Args:
        text: Passage to measure.

    Returns:
        The average ratio, or None when there is no complete window.
    """
    tokens = words(text)
    window_size = config.STYLE_VOCABULARY_WINDOW
    window_count = len(tokens) - window_size + 1
    if window_count <= 0:
        return None

    unique_total = sum(
        len(set(tokens[start : start + window_size]))
        for start in range(window_count)
    )
    return unique_total / (window_count * window_size)


def punctuation_density(text: str) -> float:
    """Return the placeholder for the unused punctuation measure."""
    _validate_text(text)
    return 0.0


def _scale_measure(value: float, limits: tuple[float, float]) -> float:
    lower, upper = limits
    return min(1.0, max(0.0, (upper - value) / (upper - lower)))


def style_signal(text: str) -> float:
    """Average the available style scores, with higher scores pointing to AI.

    Args:
        text: Passage to score.

    Returns:
        A score from 0 to 1, or 0.5 when neither measure is available.

    Raises:
        TypeError: The passage is not a string.
        ValueError: The passage is blank.
    """
    measures = (
        (sentence_length_spread(text), config.STYLE_SENTENCE_SPREAD_RANGE),
        (type_token_ratio(text), config.STYLE_VOCABULARY_RATIO_RANGE),
    )
    scores = [
        _scale_measure(value, limits)
        for value, limits in measures
        if value is not None
    ]
    return statistics.mean(scores) if scores else 0.5


if __name__ == "__main__":
    text = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else (
            "The system works well. It handles most cases correctly and "
            "provides good results. Users generally find it easy to use and "
            "understand."
        )
    )

    for name, reading in (
        ("sentence_length_spread", sentence_length_spread(text)),
        ("type_token_ratio", type_token_ratio(text)),
    ):
        value = "unavailable" if reading is None else f"{reading:.4f}"
        print(f"{name:<24} {value}")
    print(f"style_signal             {style_signal(text):.4f}")
