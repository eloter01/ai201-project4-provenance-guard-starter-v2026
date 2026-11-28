# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

## What This Does

Provenance Guard is a local service designed to give a writing site a
reader-facing label for a submission. A writer can appeal the decision.
See the [API contract](docs/API_CONTRACT.md) for request and response fields.

1. **Validate the request.** The `POST /submit` handler in `app.py` checks
   that the JSON body is an object with nonblank `text` and `creator_id`
   strings. It passes the validated text to the two signals.
2. **Score predictability.** The local detector in `detector.py` takes up to
   the first 400 model tokens and returns `model_score`. It requires at least
   three tokens to score the text.
3. **Score writing style.** `stylometry.py` takes the full submitted text and
   returns `style_score` based on sentence length spread, word variety, and
   punctuation density.
4. **Combine the scores.** `scoring.py::combine_signals` takes both signal
   scores and produces one score from 0 to 1. Higher values point toward AI.
5. **Choose a label.** `scoring.py::score_to_label` compares the combined
   score with the configured cutoffs and returns a `human`, `unsure`, or
   `ai` guess and the corresponding plain-English label.
6. **Record the decision.** The handler assigns a `content_id`. `audit.py`
   appends a `decided` entry to `logs/audit.jsonl` with the timestamp, both
   IDs, both signal scores, the combined score, the guess, and the label.
7. **Return the response.** The handler returns JSON with `content_id`,
   `guess`, `confidence` (the combined score), `label`, `model_score`, and
   `style_score`. The writing site displays the `label` to the reader.

---

## Signals and Scoring

### Signal one — the model signal

**What it measures**

The local language model measures how predictable each token is given the
tokens before it. This measure is called perplexity. Lower perplexity means
the text is easier for the model to predict and earns a higher AI score.

**Why it might differ**

AI-generated prose can favor likely word choices and familiar phrases.
People sometimes use words or details that the model finds less predictable.

**What it misses**

A person writing plain instructions can use common words and familiar
phrases throughout and receive a high AI score. The model sees patterns in
the text, while who wrote it and how they wrote it are outside its view.

### Signal two — the style signal

**What it measures**

The planned style signal measures how much sentence lengths vary, what
share of words are unique, and how often punctuation appears.

**Why it might differ**

Generated prose can use similarly sized sentences and repeat familiar words.
A person might mix short instructions with longer explanations and use
punctuation differently as the rhythm changes.

**What it misses**

The style signal has no access to meaning. Splitting a long sentence into
two can change the measured sentence lengths and punctuation while
preserving what the text says. A one-sentence submission provides no
evidence about how length varies between sentences.

### The combining rule

<!-- Write the rule in words, then give the numbers. What happens when the two
     signals disagree? -->

**The rule:**

**The numbers:**

**Where it lives:** `scoring.py::combine_signals`

<!-- ⚠️ The grader checks your code against that line. If your rule lives
     somewhere else, say where. -->

**A case where my two signals split, and what my rule does with it:**

### A false positive and appeal

In this example, a writer sends `POST /submit` with `creator_id` set to
`writer-24` and the following note as `text`.

> I opened the shop at eight and put the bread on the front shelf. Then I
> checked the till and counted the change. It was raining, so I put the mat
> by the door and wiped the floor near the entrance. The first customer
> came in for bread and milk. After she left, I called our supplier to ask
> when the next order would arrive. He said the van would come after lunch.
> I wrote that down, put the note beside the till, and went back to stocking
> the shelf.

Suppose both signals give this human-written note `0.65` and the combined
score is `0.65`. That is the starter AI cutoff, so the guess is `ai`. The
service appends a `decided` audit entry before returning `200 OK` with the
label the reader sees.

```json
{
  "content_id": "51ab2c21-39f3-41ec-8a61-d58b64aea4fd",
  "guess": "ai",
  "confidence": 0.65,
  "label": "This text looks likely to have been generated by AI. You can submit an appeal to request a review.",
  "model_score": 0.65,
  "style_score": 0.65
}
```

The writer sends `POST /appeal` with the returned `content_id` and an
explanation.

```json
{
  "content_id": "51ab2c21-39f3-41ec-8a61-d58b64aea4fd",
  "reasoning": "I wrote this from my notes about that morning. I can share the notes for review."
}
```

The service appends an `appeal` entry for the same `content_id` with the
writer's reasoning and the new status, `under_review`. The original
`decided` entry remains in the log. The appeal returns `200 OK`.

```json
{
  "content_id": "51ab2c21-39f3-41ec-8a61-d58b64aea4fd",
  "status": "under_review"
}
```

Raising the AI cutoff widens the `unsure` band. Some human-written
submissions like this one would avoid a false accusation, while some
AI-written submissions near the cutoff would also receive `unsure` and be
harder to flag.

---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human |  |  |
| unsure |  |  |
| high-confidence AI |  |  |

**Why I worded the "unsure" one this way:**
<!-- It's the hardest of the three. It has to admit uncertainty without
     sounding like an accusation, because the person reading it may well have
     written every word themselves. -->



---

## Sample Run

The service used cached GPT-2 weights with `HF_HUB_OFFLINE=1`.

**Smoke test**

```powershell
'{"message":"hello"}' | curl.exe --silent --show-error --max-time 60 --write-out '\n%{http_code}\n' -H 'Content-Type: application/json' --data-binary '@-' http://127.0.0.1:5000/ping
```

HTTP `200`

```json
{
  "ok": true,
  "service": "provenance-guard",
  "you_sent": "hello"
}
```

**Valid submission (458 characters)**

```powershell
$text = @(
  'I went to the community garden before breakfast to water the tomatoes.'
  'A loose board had fallen across the path, and the hose was kinked beneath it.'
  'I moved the board, carried the hose back to the tap, and checked the soil before watering.'
  'The plants near the fence were still damp, so I left them alone.'
  'By the time I finished, the volunteer who looks after the herbs had arrived.'
  'We agreed to hang the hose beside the shed so the next person could find it.'
) -join ' '
$payload = @{text = $text; creator_id = 'milestone-3-demo'} | ConvertTo-Json -Compress
$payload | curl.exe --silent --show-error --max-time 60 --write-out '\n%{http_code}\n' -H 'Content-Type: application/json' --data-binary '@-' http://127.0.0.1:5000/submit
```

HTTP `200`

```json
{
  "confidence": 0.5,
  "content_id": "bdad0e64-bdb5-41d3-9ad5-2076097e97e2",
  "guess": "unsure",
  "label": "We are unsure who wrote this text.",
  "model_score": 0.5868,
  "style_score": null
}
```

**Submission missing `text`**

```powershell
'{"creator_id":"milestone-3-demo"}' | curl.exe --silent --show-error --max-time 60 --write-out '\n%{http_code}\n' -H 'Content-Type: application/json' --data-binary '@-' http://127.0.0.1:5000/submit
```

HTTP `400`

```json
{
  "error": "invalid_field",
  "message": "'text' must be a nonblank string."
}
```

**Audit log**

```powershell
curl.exe --silent --show-error --max-time 60 --write-out '\n%{http_code}\n' 'http://127.0.0.1:5000/log?limit=2'
```

HTTP `200`

```json
{
  "count": 2,
  "entries": [
    {
      "combined_score": 0.5,
      "content_id": "bdad0e64-bdb5-41d3-9ad5-2076097e97e2",
      "creator_id": "milestone-3-demo",
      "guess": "unsure",
      "label": "We are unsure who wrote this text.",
      "model_score": 0.5868,
      "status": "decided",
      "style_score": null,
      "timestamp": "2026-11-28T18:09:27+00:00"
    },
    {
      "creator_id": "milestone-3-demo",
      "event": "rejected",
      "reason": "invalid_field",
      "status": "rejected",
      "timestamp": "2026-11-28T18:09:27+00:00"
    }
  ]
}
```

<!-- Add the appeal request, response, and audit entry in Milestone 5. -->

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "...", "reasoning": "..."}'
```

```json

```

---

## How I Used AI

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** ___ per minute, ___ per day

**Why those numbers and not others:**
<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->

**What a caller counts as:** <!-- per address, or per creator_id? They fail
differently — one script can look like a thousand callers, and one household
can look like one. -->

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```

```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |
| 2.  |  |  |  |  |  |
| 3.  |  |  |  |  |  |
| 4.  |  |  |  |  |  |
| 5.  |  |  |  |  |  |

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

**Diagnoses**

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
