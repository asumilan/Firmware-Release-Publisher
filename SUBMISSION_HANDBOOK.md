# Submission Handbook — What "Done" Means & How to Submit

Read this together with `CANDIDATE_GUIDE.md`. That guide explains the *problem*;
this handbook defines when your work is **complete** and how to **package and
submit** it. Most failed submissions in past cycles failed here, not on coding —
usually a missing `instruction.md`, a solution that wasn't actually verified, or
a Mac-zipped folder full of junk files. Do not skip this document.

---

## 1. What you are actually delivering

You are authoring a complete, self-contained evaluation task: a broken/empty
scenario, a precise brief, a working reference solution, and an automated grader.
Think of it as writing an exam **and** its answer key. A pile of code is NOT a
submission. A submission is the whole task folder with every required part
present and two proofs passing (Section 3).

---

## 2. A complete task = these six parts, all present

Your submitted folder MUST contain all of these. A missing part = automatic fail,
no matter how good the rest is.

| # | Path | What it is | Common mistake |
|---|------|-----------|----------------|
| 1 | `instruction.md` | The brief the solver reads. What to build, where, the rules, success condition. **You write this.** | **Left as the stub / omitted entirely — the #1 reason submissions fail.** |
| 2 | `task.toml` | Metadata: category, difficulty, languages, timeouts, author fields, time estimates. | Left with `scaffold` / `unknown` values. |
| 3 | `environment/` | The world the solver gets: Dockerfile, provided service, fixtures, keys, empty `publisher/`. | Baking the solution into it; junk files. |
| 4 | `solution/publish.sh` | **Your reference solution.** Proves the task is solvable. | Left as the no-op stub. |
| 5 | `tests/test.sh` + `tests/test_outputs.py` | The automated grader (pytest → 0/1 reward). | Doesn't recompute expected results; hardcoded answers. |
| 6 | `AUTHOR_NOTES.md` | 1–2 pages: your design, each trap, how you verified 0/1. | Omitted. |

> If you submit without `instruction.md` (part 1), the task cannot be evaluated —
> there is nothing telling the solver what to do. This is the single most common
> cause of rejection. Write it.

---

## 3. The two proofs — a task is "done" only when BOTH pass

Everything hinges on two runs in a freshly built container:

**Proof A — the empty run scores 0.**
With NO solution installed, the grader must fail and write reward `0`. This
proves the task is actually unsolved to begin with.

**Proof B — your reference solution scores 1.**
After running `solution/publish.sh`, the grader must pass and write reward `1`.
This proves the task is solvable and the grader is correct.

If A isn't 0 or B isn't 1, your task is **not done** — do not submit.

cd <task>/environment
docker build -t task-img .

Proof A (expect reward 0):
docker run --rm -it -v "$PWD/../tests":/tests:ro task-img bash -lc 

'bash /tests/test.sh; cat /logs/verifier/reward.txt'

Proof B (expect reward 1):
docker run --rm -it -v "$PWD/../tests":/tests:ro -v "$PWD/../solution":/solution:ro 

task-img bash -lc 'bash /solution/publish.sh && bash /tests/test.sh; cat /logs/verifier/reward.txt'



---

## 4. Definition of Done — the checklist

Tick every box before you zip. If any box is unchecked, you are not finished.

**Completeness**
- [ ] All six parts from Section 2 exist and are filled in (no stubs left).
- [ ] `instruction.md` is written, in your own words, and names every path the
      grader touches (absolute paths).
- [ ] `AUTHOR_NOTES.md` explains your design and traps.

**Correctness (the two proofs)**
- [ ] Empty run → reward `0` (Proof A).
- [ ] `publish.sh` run → reward `1` (Proof B).
- [ ] Running the solution twice is safe and produces identical output
      (idempotent, deterministic).

**Quality & fairness**
- [ ] The solution genuinely derives its output from the inputs — nothing
      hardcoded (row counts, receipts, golden text).
- [ ] Tests verify behavior by recomputing expected results, not by trusting
      a value the solver could fake.
- [ ] A solver could not cheat by editing fixtures, reading the service's
      private data, or bypassing verification.
- [ ] Every rule the grader enforces is stated in `instruction.md` (or its
      referenced spec). No hidden rules.
- [ ] The provided service under `environment/` is unchanged.

**Packaging (see Section 6)**
- [ ] No `jobs/`, `node_modules/`, `.DS_Store`, `__MACOSX/`, or `*.duckdb`
      runtime files in the folder.
- [ ] Zip created from the terminal (not Finder).

---

## 5. What a GOOD submission looks like (vs a failing one)

**Failing submission (real pattern we see):**
- `instruction.md` still the placeholder stub.
- `publish.sh` still `exit 0`.
- "It works on my machine" — but Proof A/B never run in a clean container.
- Folder zipped from Finder → contains `__MACOSX/` and `.DS_Store`.

**Passing submission:**
- All six parts present and real.
- Both proofs demonstrated (paste the two `reward.txt` outputs into
  `AUTHOR_NOTES.md`).
- Solution derives everything; tests recompute; no cheat path.
- Clean, terminal-made zip.

---

## 6. How to package & submit

1. **Clean the folder** of runtime junk:
cd <task-parent>
find <task> -name ".DS_Store" -delete
rm -rf <task>/jobs <task>/environment/node_modules <task>/*.duckdb


2. **Zip from the terminal** (Finder zips inject `__MACOSX`/AppleDouble files
that break automated checks):
zip -r <task>.zip <task> -x ".DS_Store" -x "/node_modules/" -x "/jobs/*"


3. **Submit** the zip to **[submission destination / email]** by **[deadline]**,
with your name and **[candidate ID]**.

---

## 7. How your submission is evaluated

- We rebuild your `environment/` from scratch and run Proof A and Proof B.
A task that doesn't score 0-then-1 is returned without further review.
- We read `instruction.md` for clarity and completeness (absolute paths, all
rules stated, no solution hints).
- We check the tests genuinely grade behavior and resist cheating.
- Shortlisted candidates walk through their task live and must explain any
line of it. **You will be asked why you made each design choice — be ready.**

---

## 8. Frequently missed points (read if you're short on time)

- **Write `instruction.md`.** Again — the most common failure is submitting
without it. The solver (and the grader) needs it.
- **Actually run the two proofs in a clean container.** "Works locally" is not
evidence; the clean 0-then-1 is.
- **Don't hardcode.** If your tests would pass on a different input only when
the solution truly computes the answer, you're good.
- **Zip from the terminal.** Finder zips fail automated packaging checks.
- **Keep the provided service untouched.** Interact with it over HTTP only.

Questions about *requirements* → **[contact]**. Questions asking for solution
help will not be answered — solving it is the assessment.

---

## 9. How to access and submit your task (portal + GitHub)

Everything above defines *when your work is done*. This section is *how you get
it to us*. Do not start these steps until both proofs pass (empty run → 0, your
solution → 1) and the Section 4 checklist is fully ticked.

### Before you push — final pre-flight

- [ ] All six parts present (Section 2), including a written `instruction.md`.
- [ ] Both proofs demonstrated in a clean container; results pasted into
      `AUTHOR_NOTES.md`.
- [ ] Folder cleaned of junk — no `jobs/`, `node_modules/`, `.DS_Store`,
      `__MACOSX/`, or `*.duckdb` runtime files (see Section 6).
- [ ] The provided service under `environment/` is unchanged.

### Submission steps

Please follow the steps below to access, complete, and submit your assigned task:

1. Log in to the portal using your registered email ID and password. After
   logging in, you will be directed to the Dashboard, where you can view all
   tasks assigned to you.
2. Click on the title of the assigned task. You will see the following sections:
   **Task Details**, **Submit**, and **Results**.
3. Click **Task Details** to view the problem statement and download the
   reference project skeleton ZIP file.
4. Download and extract the ZIP file on your local machine. Open and read the
   `candidate_guide.md` file carefully for detailed instructions and the actions
   required to complete the assignment.
5. Before starting the assignment, create a **public GitHub repository**. Add the
   downloaded project files to the repository and complete the assignment within
   the same repository.
6. Ensure that all required files and completed code are committed and pushed to
   the public GitHub repository.
7. Once the assignment is complete, return to the portal and click the **Submit**
   section.
8. Enter the complete public GitHub repository URL and submit it. The submitted
   repository link will be shared with the reviewer for evaluation and further
   steps.
9. You will have a **maximum of 3 submissions** allowed for this assignment.

### Two reminders that protect your submission

- **Commit `instruction.md` and `solution/` to the repo.** The most common
  failure is a repository missing the instructions or the reference solution —
  the reviewer clones exactly what you push, nothing more.
- **You have only 3 submissions.** Because that budget is small, run both proofs
  in a clean container *before* your first submit. Treat submission 1 as a
  finished task, not a trial.

