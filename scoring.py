"""Combine authorship signals and map scores to labels."""

from numbers import Real

import config


def _validate_signal_score(score: float, name: str) -> None:
    if isinstance(score, bool) or not isinstance(score, Real):
        raise TypeError(f"{name} must be a real number.")
    if not 0 <= score <= 1:
        raise ValueError(f"{name} must be finite and between 0 and 1.")


def combine_signals(model_score: float, style_score: float) -> float:
    """Blend two scores and require agreement at the AI cutoff.

    Args:
        model_score: Score for text predictability, from 0 to 1.
        style_score: Score for writing style, from 0 to 1.

    Returns:
        The weighted average, or the midpoint of the unsure range if the
        average reaches the AI cutoff and either score is below it.

    Raises:
        TypeError: Either score is nonnumeric or a boolean.
        ValueError: Either score is outside the finite range from 0 to 1.
    """
    _validate_signal_score(model_score, "model_score")
    _validate_signal_score(style_score, "style_score")

    average = (
        config.WEIGHT_MODEL_SIGNAL * model_score
        + config.WEIGHT_STYLE_SIGNAL * style_score
    )
    if average >= config.AI_THRESHOLD > min(model_score, style_score):
        return (config.HUMAN_THRESHOLD + config.AI_THRESHOLD) / 2
    return average


def score_to_label(score: float) -> tuple[str, str]:
    """
    Turn a score into a guess and the text a reader actually sees.
    ← TODO (Milestone 5)

    Returns:
        (guess, label_text) — where `guess` is a short machine-readable string
        like "ai" / "human" / "unsure", and `label_text` is the full sentence
        shown to a person.

    ⚠️ Write the label text for someone who has never heard the word
    "threshold".

        ✗ "human, 0.81 confidence"
        ✓ "We think this was probably written by a person."

    All three labels have to be **reachable**. If no score can produce one of
    them, your ranges have a gap — and Milestone 5 asks you to submit text that
    produces each one, which is how you'd find out.

    The hardest one to write is "unsure". It has to admit uncertainty without
    sounding like an accusation, because the person reading it may well have
    written every word themselves. Your breakout asks your group what they'd
    think if they got it on their own work. That question is the whole
    milestone.
    """
    # TODO: replace this — thresholds are in config.py
    if score >= config.AI_THRESHOLD:
        return "ai", "PLACEHOLDER — write the high-confidence AI label."
    if score <= config.HUMAN_THRESHOLD:
        return "human", "PLACEHOLDER — write the high-confidence human label."
    return "unsure", "PLACEHOLDER — write the unsure label."


def label_ranges() -> list[tuple[str, str]]:
    """
    The score range each label covers. Your README needs these beside the
    label text — given to you so the numbers can't drift apart from config.py.
    """
    return [
        ("high-confidence human", f"0.00 – {config.HUMAN_THRESHOLD:.2f}"),
        ("unsure", f"{config.HUMAN_THRESHOLD:.2f} – {config.AI_THRESHOLD:.2f}"),
        ("high-confidence AI", f"{config.AI_THRESHOLD:.2f} – 1.00"),
    ]
