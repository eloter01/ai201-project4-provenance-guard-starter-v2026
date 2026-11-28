import math

import pytest

from stylometry import sentence_length_spread, style_signal, type_token_ratio


def test_sentence_spread_distinguishes_uniform_and_varied_lengths() -> None:
    uniform = "We walk home. They stay here."
    varied = "Wait. ... We walked home after dark."

    assert sentence_length_spread(uniform) == 0.0
    assert sentence_length_spread(varied) == pytest.approx(math.sqrt(8) / 3)
    assert style_signal(uniform) > style_signal(varied)


def test_vocabulary_variety_uses_windows_across_full_text() -> None:
    repeated_prefix = "echo " * 20
    varied_suffix = " ".join(f"word{index}" for index in range(20))

    assert type_token_ratio(repeated_prefix) == 0.05
    # The 21 windows contain 1 through 20 unique words, then 20 again.
    assert type_token_ratio(repeated_prefix + varied_suffix) == pytest.approx(
        23 / 42
    )


def test_style_signal_uses_only_eligible_measures() -> None:
    one_sentence = "echo " * 20
    two_short_sentences = "We walk home. They stay here."
    two_varied_sentences = (
        "We watched robins dart from maple branches into distant hedges. "
        "Neighbors gathered outside while children chased butterflies across "
        "sunlit grass."
    )

    assert sentence_length_spread(one_sentence) is None
    assert style_signal(one_sentence) == 1.0
    assert type_token_ratio(two_short_sentences) is None
    assert style_signal(two_short_sentences) == 1.0
    assert style_signal(two_varied_sentences) == 0.5


@pytest.mark.parametrize(
    "text", ["some writing here", "echo " * 19, "... !? ' ’ —"]
)
def test_style_signal_is_neutral_without_evidence(text: str) -> None:
    assert sentence_length_spread(text) is None
    assert type_token_ratio(text) is None
    assert style_signal(text) == 0.5


def test_style_signal_scale_is_bounded() -> None:
    repeated_sentence = "echo " * 9 + "echo."
    varied = (
        "Clang. My neighbor dropped the brass latch, which skidded across "
        "wet cobblestones and vanished beneath an overturned wheelbarrow. "
        "We waited."
    )

    assert style_signal(f"{repeated_sentence} {repeated_sentence}") == 1.0
    assert style_signal(varied) == 0.0


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("", ValueError),
        (" \t\n", ValueError),
        (None, TypeError),
        (42, TypeError),
        (["writing"], TypeError),
    ],
)
def test_stylometry_rejects_blank_and_non_string_input(
    text: object, error: type[Exception]
) -> None:
    for measure in (sentence_length_spread, type_token_ratio, style_signal):
        with pytest.raises(error):
            measure(text)
