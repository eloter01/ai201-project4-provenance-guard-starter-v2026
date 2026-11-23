## Background

We will build **Provenance Guard**, a small backend service a writing site could plug into. Text comes in. What comes back is a guess, a number saying how confident that guess is, a plain-English label the reader would see, and a way for the writer to push back. 

### Goals

* Build an endpoint that takes JSON in and sends structured JSON back  
* Combine two different signals into one number  
* Turn a number into something a non-technical reader would understand  
* Write acceptance criteria for a system where being wrong has a cost

## Requirements

1. **criteria.md** — five numbered acceptance criteria, each naming a target.   
2. **README.md** — the five sections listed at the bottom of this page.

### Features

1. **A POST /submit endpoint.** Takes JSON with text and creator\_id. Returns JSON with a content\_id, a guess, a confidence score, and the label text.  
2. **Two signals that measure different things.** One reads the text for meaning. One measures it as text — sentence length spread, word variety, punctuation. Two versions of the same idea don't count as two.  
3. **A confidence score that varies.** 0.51 and 0.95 must produce different labels. A flip at 0.5 is not confidence.  
4. **Three label variants**, written out in full: high-confidence AI, high-confidence human, and unsure. Every reachable score maps to one of them.  
5. **A POST /appeal endpoint.** Takes a content\_id and the writer's reasoning. Records it, moves the item to under\_review, and confirms. No automatic re-checking needed.  
6. **Five acceptance criteria**

**RUNNING.md in the repo is your reference for everything else** — every command, which route is built and which is yours, what each file does, and the troubleshooting table. Read it now, and come back to it whenever you're stuck.

We will be using a web service.

**The first submission takes ten seconds or more** while signal one loads the model into memory. Later ones take a second or two. If *every* submission is slow, something is reloading the model on each call — GET /health shows detector\_loaded, and if that flips back to false you have a reload in your handler.

### **Milestone 1: Trace a submission before you build one**

Seven pieces have to work together. Build them one at a time without knowing how they connect, and you get a service that works feature by feature and breaks at the seams.

So let’s write the path down first, in plain English.

* Write the path a piece of text takes from arriving to the label a reader sees. Name each thing it passes through and what that thing adds. Six or seven steps.  
* Name what your two signals measure. Signal one is detector.py, given to you — a local model reading the text. Signal two is yours to build in stylometry.py, measuring the text as text. For each, write what property it measures, why that property might differ between human and AI writing, and **what it can't see**. If you can't name the blind spot, you don't understand the signal yet.  
  Both blind spots are real and the next unit's attack set is built out of them, so this is not a warm-up exercise.  
* Trace the false positive. A real writer submits real work and your system calls it AI. Follow that person through your service. What score did they get? What did the label say to them? What can they do about it?  
  This is the scenario that decides your thresholds. Everything in Milestone 4 comes back to it.  
* Write the shape of your two endpoints: what goes in, what comes out, field by field. You're not coding — you're deciding the contract everything else has to keep.  
  Then read it back and ask whether someone else could build against it without asking you a question.

**Before you move on**

You can describe the path end to end and name both signals with their blind spots. Your two endpoint shapes are written down. Commit.

 **Milestone 2: Write your acceptance criteria**

An acceptance criterion says what "working" means, specifically enough that someone else could check it. Not *"the detector is accurate"* — that's an opinion, and perfect AI detection isn't possible anyway. *"Of 10 pieces I wrote myself, at most 1 is labeled high-confidence AI"* — that's a criterion. It names a number.

You're writing them **before you build**. Afterwards we find out how you did against a standard you set when you couldn't know the answer.

Setting a target so easy you can't miss it is bad practice.

* Create criteria.md and write five numbered criteria. Cover at least three of these:

| Area | A question it could answer |
| ----- | ----- |
| False positives | How often may a human's writing get called AI? |
| Score spread | How far apart should clearly-AI and clearly-human text score? |
| Label coverage | Is every one of your three labels actually reachable? |
| The appeal path | Does an appeal always change status and always get recorded? |
| Bad input | What happens when text is missing, empty, or enormous? |

*   
* Give every criterion a number or something plainly observable. "The system handles uncertainty well" is not a criterion. "Text I judge borderline scores between 0.4 and 0.6 in at least 4 of 5 cases" is.  
* Under each, write a sentence or two on why that target. *"I allow at most 1 false positive in 10 because on a writing site a wrong accusation costs more than a missed detection"* is a real answer.

As you write each criterion, ask it whether each one could be checked by someone who couldn't ask you what you meant.

**Before you move on**

criteria.md has five numbered criteria. Each names a number or an observable outcome. Each has a reason underneath. Commit.

### **Milestone 3: Get the endpoint running with one signal**

One route, one signal, one real response. Don't add the second signal yet.

One working signal is easy to debug. Two broken ones are not, and you can't tell which is lying.

* Fill in app.py::submit, replacing the 501. Accept JSON with text and creator\_id. **Return a hardcoded response first and confirm curl gets it back before you add any logic** — that's how you tell a broken route from a broken signal later.  
* Run your first signal on its own before wiring it in:

```
python detector.py "some writing here"
```

*   
  Do that with three pieces of text — something you're sure is AI, something you're sure is human, something in between. Read the three outputs before wiring anything.  
* Wire the signal into the route. The response now carries a content\_id, the first signal's result, and placeholder values for confidence and label. **The content\_id matters** — the appeal endpoint needs it.  
* Write every submission to the audit log through audit.py, which is given to you: timestamp, content id, creator id, the guess, the first signal's score, and a status. It writes structured JSON to logs/audit.jsonl. Not print() — a file you can read back.  
* Check it worked. GET /log already works in the starter and returns the recent entries as JSON, so you don't build it — you use it to see whether your log entries are actually landing. Test both routes with curl and paste the requests and responses into your README under **Sample Run**.

Route not responding? Go back to /ping, the starter's untouched example route, and confirm *that* answers. If it does, the problem is in your handler. If it doesn't, it's the service itself and that's a help-channel question. On Windows, check you're using curl.exe on one line before assuming your code is wrong.

Signal not working? Have it return a fixed number, write a comment saying so, and move on.

**Before you move on**

POST /submit returns JSON with a content\_id and a real signal result. Every call writes an entry to logs/audit.jsonl. GET /log shows them. Commit — the log file is not gitignored, on purpose.

### **Milestone 4: Add the second signal and score confidence**

Now the pipeline becomes multi-signal, and you have to turn two numbers into one.

The scoring function is where your false-positive decision from Milestone 1 actually gets made, and a careless one undoes everything on top of it.

* Build your second signal in stylometry.py, where the stubs are waiting. Compute two or three things — sentence length spread, the ratio of unique words to total words, punctuation density — and combine them into one score. Test it from a terminal on its own: python stylometry.py "some writing here".  
* Run both signals over the same three test pieces. Where do they agree? Where do they disagree? Write down one case where they split, because that case is what your combining rule has to handle.  
* Write the combining rule in scoring.py::combine\_signals. Weighted average, a rule about disagreement, or something else — but write the rule down before you code it, and put the numbers in the README. The weights and thresholds live in config.py.  
* Test with four deliberately chosen inputs: clearly AI, clearly human, formal human writing, and lightly-edited AI. The last two are the ones that matter. If a score surprises you, print both signals separately to find which one is off. Then update the log to record both signal scores alongside the combined one — in the next unit you can't diagnose anything without them.

Scores not separating? Print both signals for all four inputs in one table and look at it.

If one signal returns nearly the same number for everything, that's your answer, and it's a real finding — write it down. A signal that doesn't discriminate is exactly the kind of thing the next unit's testing is meant to surface.

**Before you move on**

Both signals run and combine into one score. Clearly-AI and clearly-human text score noticeably apart. The log records all three numbers. Commit.

### **Milestone 5: Write the label and the appeal path**

The last two pieces are the ones a real person actually meets. A score of 0.62 means nothing to a writer. The label is where you say what you mean.

* Write the exact text of all three labels. Full sentences, as a reader would see them. Put them in your README under **Label Variants**, along with the score range each one covers.  
  Write them for someone who has never heard the word "threshold." *"We think this was probably written by a person"* beats *"human, 0.81 confidence."*  
* Fill in scoring.py::score\_to\_label and wire it into the response. Then submit text that produces each of the three. If a label can't be reached, your ranges have a gap — scoring.label\_ranges() prints them so you can see where it is.  
* Build app.py::appeal. It takes a content\_id and the writer's reasoning, sets the status to under\_review, writes the appeal into the log next to the original decision, and confirms. Test it with a real content\_id from an earlier submission, check GET /log shows the new status, and paste both into your README under **Sample Run**.

Appeal endpoint not writing to the log? Check the simplest thing first — does the content\_id you're sending actually exist in the log? A typo there fails silently and looks like a broken endpoint.

Still stuck? Commit what you have and write down what the appeal returned and what the log showed. That gap is what we diagnose in the next phase.

**Before you move on**

All three labels are reachable and written out in your README. An appeal changes status and shows in the log. Commit.

### **Milestone 6: Write it up and submit**

You already wrote most of it as you went.

* Fill in **What This Does** and **How I Used AI**. For AI use, describe two specific moments — what you asked, what came back, what we changed.  
* In **Signals and Scoring**, name the file and function that holds your combining rule. The grader checks your code against what you claim, so scoring.py::combine\_signals is what that line looks like. Then check the repo — criteria.md, five README sections, logs/audit.jsonl committed, four new commits or more.

