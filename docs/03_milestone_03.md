# Milestone 3 Plan — Get the Endpoint Running With One Signal

## Goal

Build `POST /submit` so it validates a request, runs the local detector, and
returns a unique `content_id` and the real `model_score`. The guess stays
`unsure` while confidence and label use placeholders. Successful submissions
and rejections are recorded in the audit log and visible through `GET /log`.

## Out of scope

- Stylometry, combined scoring, final labels, appeals, and rate limiting.
- A maximum character count for submission text.
- Cleanup of existing Ruff findings.

## Steps

After each step, run `python -m ruff check .`,
`python -m ruff format --check .`, and `python -m pytest -q`. Compare both
Ruff results with the existing baseline and keep new code formatted. Add
each pytest case alongside its code. Review one change per turn and commit
only after the user says `commit it`.

1. **Make the route answer with hardcoded JSON.** Replace the `501` stub in
   `app.py` with a `200` response using the planned response fields. Use a
   sample ID, an `unsure` guess, and placeholders. Confirm the response with
   Windows `curl.exe` before adding validation or model calls.

   **Checks in `tests/test_submit.py`**

   - `test_submit_returns_json_response` verifies the status and response
     shape.
   - `test_ping_remains_available` verifies the smoke-test control.

   **Commit** `feat(submit): add a hardcoded JSON response`

2. **Validate inputs and audit rejected requests.** In `app.py`, require a
   JSON object containing nonblank string values for `text` and `creator_id`.
   Return a JSON `400` on invalid input and append a rejection through
   `audit.log_rejection`. Record the reason and a valid creator ID when
   available, with `unknown` as the fallback. Point the tests at a temporary
   audit file.

   **Checks in `tests/test_submit.py`**

   - `test_submit_rejects_malformed_and_non_object_json` covers malformed
     JSON, arrays, scalars, and `null`.
   - `test_submit_rejects_invalid_required_fields` covers missing, null,
     wrong-type, empty, and whitespace-only values for both fields.
   - `test_submit_audits_rejections` verifies one rejection entry and the
     creator ID fallback.
   - `test_submit_accepts_text_over_400_characters` checks the agreed length
     behavior.

   **Commit** `feat(submit): validate requests and audit rejections`

3. **Wire in the detector and record decisions.** Before wiring it up, run
   `python detector.py` separately on a known AI passage, a known human
   passage, and a borderline passage. Read all three scores. Then call
   `detector.model_signal(text)` from `app.py` and generate a unique ID for
   each scored submission. Append one decision through `audit.log_decision`
   before returning `200`. Return the model score with `guess` set to
   `unsure`, `confidence` set to `0.5` as a placeholder, a provisional
   label, and `style_score` set to `null`. In `detector.py`, give the
   existing minimum-token failure a distinct exception so the route can
   return `400` for text under three model tokens. Return JSON `503` when
   the detector cannot load. Audit both failures and surface audit write
   failures as JSON `500`.

   **Checks in `tests/test_submit.py` and `tests/test_detector.py`**

   - `test_submit_returns_and_audits_model_score` checks that the response
     and audit row share the ID, guess, and score.
   - `test_submit_assigns_distinct_content_ids` checks repeated submissions.
   - `test_detector_requires_three_tokens` covers the two- and three-token
     boundary.
   - `test_submit_audits_text_too_short` expects `400` and a rejection entry.
   - `test_submit_audits_unavailable_detector` expects JSON `503` and a
     rejection entry.
   - `test_submit_returns_error_when_audit_write_fails` expects JSON `500`.

   Stub model calls in the route tests so pytest can run without downloading
   the model.

   **Commit** `feat(submit): score submissions and record audit decisions`

4. **Capture the live sample run.** Add the actual `curl.exe` requests and
   responses from the final check to **Sample Run** in `README.md` and
   include the matching entries in `logs/audit.jsonl`. Use a demo creator
   ID for the recorded requests.

   **Checks**

   - _Response matches audit record_ verifies the content ID, model score,
     guess, and `decided` status.
   - _Rejection is visible_ verifies that the invalid request appears in
     `/log` as a rejection.

   **Commit** `docs(readme): record the milestone 3 sample run`

## Final step

Start Flask and check `/ping`. Submit a valid passage longer than 400
characters with `curl.exe` and verify a `200`, a unique `content_id`, an
`unsure` guess, and a real `model_score` between `0` and `1`. Send a request
with missing `text` and verify JSON `400`. Fetch `/log` and confirm that it
shows the matching decision and rejection. Use the automated
detector-unavailable case to verify JSON `503`.

## Risks

- A cold start may require downloading the model and can be slow. The live
  check needs a working local model, while pytest uses stubs.
- The detector's three-token minimum and 400-token inference window are
  separate from HTTP validation. The route accepts longer passages, and the
  detector scores its configured window.
