# Milestone 1 Plan — Trace a Submission

## Goal

Document the seven steps from a writer's submission to the label a reader
sees, including what each signal measures and where it can mislead. Define
`POST /submit` and `POST /appeal` field by field so someone can build against
the contract, then show how a wrongly flagged writer can appeal and move the
submission to `under_review`.

## Out of scope

- Implementing routes, stylometry, score combination, label mapping, or audit
  writes.
- Calibrating weights and numeric cutoffs, finalizing label copy, or writing
  Milestone 2 acceptance criteria.
- Cleaning up existing Ruff findings.

## Steps

After each step, run `python -m ruff check .`,
`python -m ruff format --check .`, and `python -m pytest -q`. Compare both
Ruff results with the existing baseline and resolve any new findings. Run
the named manual checks alongside each documentation change. The repository
hook accepts pytest's no-tests result while the suite is empty. Review one
change per turn and commit only after the user says `commit it`.

1. **Document the submission path and both signals.** Fill in **What This
   Does** and the two signal sections in `README.md`. Give request validation,
   the local detector, stylometry, score combination, label selection, audit
   recording, and the JSON response that supplies the reader's label one step
   each. For each signal, explain what it measures, why that property might
   differ between human and AI writing, and what it can't see. Predictable
   prose can come from a human, and writing patterns can change while the
   meaning stays the same.

   **Checks**

   - _Seven-stage handoff_ verifies what each stage receives and adds.
   - _Plain human prose_ checks that the model notes explain how predictable
     human writing can receive a high AI score.
   - _Single-sentence submission_ checks that the style notes explain why one
     sentence provides no evidence about variation between sentences.

   **Commit** `docs(readme): trace submissions and explain signal limitations`

2. **Define both endpoint contracts.** Add `docs/API_CONTRACT.md` and link it
   from `README.md`. For `/submit`, document the required `text` and
   `creator_id` strings and the `200` response fields `content_id`, `guess`,
   `confidence`, `label`, `model_score`, and `style_score`. Define all three
   scores on a 0–1 scale, rising toward AI, and define `guess` as `human`,
   `unsure`, or `ai`. Scores equal to either cutoff receive the corresponding
   high-confidence label. The API accepts text without a maximum character
   count. The detector uses its configured window of up to 400 tokens, and
   stylometry measures the full submitted text. For `/appeal`, document the
   required `content_id` and `reasoning` strings, the `200` confirmation with
   `content_id` and `status: under_review`, and the appended audit entry tied
   to the original decision. Give both routes request and response examples
   and a JSON error shape with `error` and `message` fields.

   **Checks**

   - _Valid submission and appeal_ verifies each field, type, and status.
   - _Long submission_ checks that otherwise valid text over 400 characters
     is accepted and that a submission over 400 model tokens illustrates
     the different text each signal sees.
   - _Invalid payload_ expects `400` for malformed or non-object JSON and for
     each required field when missing, null, the wrong type, or blank.
   - _Too short to score_ expects `400` when the detector receives fewer than
     three tokens.
   - _Unknown content ID_ expects `404` for a well-formed appeal whose ID
     does not match a recorded decision.
   - _Score boundaries_ covers `0`, `1`, and scores just below, exactly at,
     and just above both cutoffs.

   **Commit** `docs(api): define submission and appeal contracts`

3. **Trace a false positive.** Add a worked example in `README.md` under
   **Signals and Scoring**. Use a hypothetical plain-language human
   submission with a combined score of `0.65`, the starter AI cutoff. Show
   the `ai` guess, an example of the exact sentence the reader would see,
   and how the writer appeals using the returned `content_id`. Follow the
   item from `decided` to `under_review` through the appended appeal entry.
   Explain how widening the `unsure` band could spare some human writers a
   false accusation while making some AI-written submissions harder to flag.

   **Checks**

   - _Human writing at the AI cutoff_ verifies the high-confidence AI guess,
     the reader-facing sentence, and the available appeal action.
   - _Appeal preserves the decision history_ verifies that the original
     decision and the appended appeal share the same ID and that the appeal
     confirms `under_review`.

   **Commit** `docs(readme): walk through a false positive and appeal`

## Final step

Use only the finished README and API contract to walk through a valid
submission longer than 400 characters. Follow all seven stages and use the
worked example's score to derive the `ai` guess and the sentence the reader
sees. Take the content ID from the response, construct the appeal, and trace
the expected `under_review` confirmation and both audit entries. Then walk
through malformed submission JSON and an appeal with an unknown ID. The
check passes when a reader can derive every request, response, label, and
status from the documents alone.

## Risks

- Short submissions remain valid when they meet the detector's minimum, and
  they can still provide weak evidence for stylometry. In Milestone 4,
  compare full passages with short excerpts, including plain human writing,
  before deciding how much weight to give the style score.
- In long submissions, the two signals may disagree if the writing style
  changes beyond the detector's window. Include a long passage in calibration
  to see how the combining rule handles that split.
- The starter's numeric cutoffs are provisional. Update the worked example
  and boundary cases together if calibration moves either cutoff.
