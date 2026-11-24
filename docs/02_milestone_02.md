# Milestone 2 Plan — Write Acceptance Criteria

## Goal

Fill `criteria.md` with five numbered acceptance criteria, one each for false
positives, score separation, label coverage, appeals, and bad input. Each
criterion will specify the inputs, a pass condition that applies to each of
three trials, and a short reason for the target.

## Out of scope

- Implementing the service, tuning thresholds, or changing the API contract.
- Collecting the evaluation samples, editing `scenarios.py` or `run_eval.py`,
  or running the live evaluation.
- Cleaning up existing Ruff findings.

## Steps

After each step, run `python -m ruff check .`,
`python -m ruff format --check .`, and `python -m pytest -q`. Compare both
Ruff results with the existing baseline and resolve any new findings. The
repository hook accepts pytest's no-tests result while the suite is empty.
Run the named manual checks in the same step. Review one change per turn and
commit only after the user says `commit it`.

1. **Set the false-positive target in `criteria.md`.** In each trial, at most
   **1 of 10 self-authored passages** may receive an `ai` guess. Use the same
   ten passages across trials and include plain human prose. Explain why
   falsely accusing a writer carries a higher cost than missing some AI
   writing.

   **Checks**

   - _One false positive passes_ checks that `1/10` meets the target.
   - _Two false positives fail_ checks that trial counts of `0, 1, 2` fail
     overall.
   - _Missing result_ checks that a request error cannot count toward ten
     successful classifications.

   **Commit** `docs(criteria): define the false-positive target`

2. **Set the score separation and label coverage targets in `criteria.md`.**
   For score separation, propose a median `confidence` at least **0.20
   higher** for ten known AI passages than for ten human passages of similar
   length in each trial. The median limits the influence of unusually high
   or low scores. For label coverage, require a fixed set of passages to
   produce at least one `human`, `unsure`, and `ai` guess in each trial, each
   with its corresponding reader-facing label. This checks that the service
   can express uncertainty as well as either high-confidence outcome.

   **Checks**

   - _Score gap at the boundary_ passes at `0.20` and fails at `0.19`.
   - _Missing score_ fails when a response lacks a numeric `confidence`.
   - _All three labels_ passes with all three guess-and-label pairs.
   - _Missing or mismatched label_ fails when `unsure` never appears or a
     guess carries the wrong label text.

   **Commit** `docs(criteria): define score separation and label coverage`

3. **Set the appeal and bad-input targets in `criteria.md`.** In each trial,
   appeal a fresh submission using its returned `content_id`. Require a `200`
   response confirming `under_review` and a matching appeal entry after the
   original decision in `/log`. For bad input, require `400` for missing,
   null, non-string, empty, or whitespace-only `text`. Include a valid
   submission over 400 characters that must return `200`. Explain why the
   appeal must leave a trace and why valid longer writing should be accepted.

   **Checks**

   - _Appeal recorded and confirmed_ verifies the ID, status, and audit
     entries.
   - _Confirmation without an audit entry_ fails.
   - _Unknown appeal ID_ checks the expected `404`.
   - _Invalid text variants_ checks every listed bad input.
   - _Valid long submission_ checks that the service accepts text beyond 400
     characters.

   **Commit** `docs(criteria): define appeal and input validation targets`

## Final step

Give a reviewer only `criteria.md`, three sets of example submission
responses, and example appeal and audit records. Have them assign a pass or
fail to all five criteria. Include a case that fails in just one trial so the
reviewer can confirm that a single failed trial fails the criterion overall.

## Risks

- The false-positive target depends on having ten genuinely self-authored
  passages. Choose the evaluation samples before seeing their scores.
- The proposed `0.20` gap is a target set before calibration. Sample length
  and topic can affect the result, so choose comparable human and AI
  passages.
- The current evaluator submits text and records responses. Plan to verify
  appeals manually with `/appeal` and `/log` in each trial.
