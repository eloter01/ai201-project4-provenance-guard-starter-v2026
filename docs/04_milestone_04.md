# Milestone 4 Plan — Add the Second Signal and Score Confidence

## Goal

`POST /submit` will return a model score, a style score, and a combined
`confidence`, with all three recorded in the audit log. Stylometry will use
sentence-length variation and vocabulary variety, and the combined score
will reach the high-confidence AI range only when both signals reach the AI
cutoff.

## Out of scope

- Punctuation density, detector tuning, final labels, appeals, and rate
  limiting.
- A maximum character count for submission text.
- The full three-trial acceptance evaluation and cleanup of existing Ruff
  findings.

## Steps

After each step, run `python -m ruff check .`,
`python -m ruff format --check .`, and `python -m pytest -q`. Compare both
Ruff results with the existing baseline and keep new code formatted. Add
each pytest case alongside its code. Review one change per turn and commit
only after the user says `commit it`.

1. **Build and test the style signal.** In `stylometry.py`, measure
   sentence-length variation as standard deviation divided by mean sentence
   length. For vocabulary variety, average unique-word ratios over rolling
   20-word windows so the measure uses the full submission at a consistent
   window size. Use standalone readings to choose and document initial
   scaling ranges in `config.py`. Scale both measures to 0–1, with higher
   scores pointing toward AI. Sentence variation needs two sentences
   containing words, and vocabulary variety needs 20 words. Average the
   available measures, use a single eligible measure on its own, and return
   `0.5` when neither qualifies. Verify the CLI with
   `python stylometry.py "some writing here"`.

   **Tests in `tests/test_stylometry.py`**

   - `test_sentence_spread_distinguishes_uniform_and_varied_lengths` compares
     equal-length sentences with varied lengths.
   - `test_vocabulary_variety_uses_windows_across_full_text` verifies that
     vocabulary later in the submission affects the score.
   - `test_style_signal_uses_only_eligible_measures` covers a single sentence
     at 20 words and a short passage with two word-bearing sentences.
   - `test_style_signal_is_neutral_without_evidence` covers a single sentence
     below 20 words and punctuation-only text.
   - `test_style_signal_scale_is_bounded` covers both ends of the scale.
   - `test_stylometry_rejects_blank_and_non_string_input` covers empty text,
     whitespace, `None`, and other non-string inputs.

   **Commit** `feat(stylometry): score sentence variation and vocabulary variety`

2. **Compare both signals and write the combining rule before coding it.**
   Run both CLIs on the same three passages, one clearly AI, one clearly
   human, and one borderline. In `README.md` under **Signals and Scoring**,
   record the measured scores, one observed disagreement, and what
   `scoring.py::combine_signals` should do in that case. Document 50/50
   weights. If the average reaches the AI cutoff and either signal falls
   below it, use the midpoint of the unsure range. With the starter cutoffs,
   that midpoint is `0.50`.

   **Manual checks**

   - _Same text for both signals_ verifies that each pair came from the same
     passage.
   - _Observed disagreement_ checks the rule against the recorded scores.
   - _AI cutoff agreement_ verifies the rule by hand using `0.90` and `0.50`,
     then `0.65` and `0.65`.

   **Commit** `docs(scoring): record signal comparison and combining rule`

3. **Implement the combining rule.** Update `scoring.py::combine_signals`
   to use the configured weights and cutoffs. Validate that both inputs are
   finite numeric scores within 0–1. Keep exact cutoff equality eligible for
   a high-confidence outcome.

   **Tests in `tests/test_scoring.py`**

   - `test_combine_signals_averages_aligned_scores` verifies the 50/50 blend.
   - `test_combine_signals_keeps_unsupported_ai_in_unsure_range` covers each
     signal taking a turn below the AI cutoff.
   - `test_combine_signals_accepts_both_scores_at_ai_cutoff` covers exact
     equality for both signals.
   - `test_combine_signals_preserves_score_endpoints` covers pairs at `0` and
     `1`.
   - `test_combine_signals_rejects_invalid_scores` covers nulls, strings,
     booleans, nonfinite values, and out-of-range numbers.

   **Commit** `feat(scoring): require both signals for high-confidence AI`

4. **Return and audit all three scores.** In `app.py`, pass the full
   validated submission to stylometry, combine the scores, and return them
   as `model_score`, `style_score`, and `confidence`. Pass the same numbers
   to `audit.log_decision`, storing `confidence` as `combined_score`. Keep
   the provisional guess and label through Milestone 4.

   **Tests in `tests/test_submit.py`**

   - `test_submit_returns_both_signals_and_combined_confidence` verifies the
     three response values with stubbed signals.
   - `test_submit_audit_matches_response_scores` matches the response to its
     decision entry by `content_id`.
   - `test_submit_passes_full_long_text_to_stylometry` verifies that
     stylometry receives the entire submission.
   - Re-run the Milestone 3 invalid-input, detector-unavailable, and
     audit-write failure cases.

   **Commit** `feat(submit): return and audit model, style, and combined scores`

5. **Record the calibration results.** Run clearly AI, clearly human, formal
   human, plain human, and lightly edited AI passages through the service.
   Include a short excerpt paired with its longer passage. Add a table of
   the three scores to `README.md` and retain matching entries in
   `logs/audit.jsonl`. If separation is weak, show which signal clustered or
   disagreed before revisiting its scaling.

   **Manual checks**

   - _Clear AI and human score separation_ records the gap.
   - _Formal and plain human writing_ compares the two false-positive cases.
   - _Lightly edited AI_ checks how edits affect each signal.
   - _Short and long versions_ checks how available style evidence changes
     the result.

   **Commit** `docs(scoring): record milestone 4 calibration results`

## Final step

Submit the calibration passages to the running service and fetch `/log`.
For each successful response, use its `content_id` to find the audit row
and verify that all three numbers match. Recompute the combined score from
the documented rule, including a disagreement case, and verify that the
clearly AI passage scores higher than the clearly human passage.

## Risks

- Requiring agreement can prevent a false accusation from one strong
  signal. It can also leave AI-written passages below the cutoff when
  stylometry has weak evidence.
- For long submissions, the detector sees up to 400 tokens while stylometry
  sees the full text. For short submissions, one or both style measures may
  be unavailable. The paired calibration case checks both effects.
