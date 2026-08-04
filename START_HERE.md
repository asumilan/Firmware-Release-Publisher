# START HERE — Read this first

Welcome, and thanks for taking this assessment. Before any code, spend five
minutes here. It explains **why** this exercise exists, **how to think** about
it, and the **end-to-end process** from opening the folder to submitting. Most
people who struggle do so because they skipped the "why" and started typing —
don't be that person.

**Read these three documents in order:**
1. `START_HERE.md` — this file (why + the big picture)
2. `CANDIDATE_GUIDE.md` — the actual task and a recommended order of work
3. `SUBMISSION_HANDBOOK.md` — what "done" means and how to submit

---

## 1. Why this exercise exists

Hurix builds **evaluation tasks for AI coding agents** — realistic, self-contained
engineering problems used to measure what today's strongest AI models can and
cannot do on their own. Companies use these measurements to decide how much to
trust AI with real engineering work.

This assessment checks whether **you** can author one of these tasks well. That
is the job you are interviewing for. It is not a LeetCode puzzle; it is a
"can you design a fair, precise, cheat-proof engineering challenge" test.

## 2. The one idea that makes everything click

**You are the examiner. The AI is the student.**

You are not solving a problem someone handed you. You are *setting an exam* for
an AI agent:

- You write the **question paper** → `instruction.md`
- You write the **answer key** → `solution/`
- You build the **grading machine** → `tests/`
- You set up the **exam hall** → `environment/` (a Docker container)

Everything else in this assessment follows from that one idea. When you're
unsure whether to do something, ask: *"What would a good examiner do?"*

A good exam has one more property: **a skilled human can solve it confidently,
but it challenges current AI models.** Fair, clear, and hard — not tricky, not
ambiguous, not impossible.

## 3. Why the task is built the way it is

A serious exam needs four things, and each maps to one part of the task:

| A good exam needs... | ...which is this file |
|---|---|
| A clear question | `instruction.md` (you write it) |
| A proven answer key | `solution/publish.sh` (you write it) |
| A machine that grades automatically | `tests/` (pytest → a 0 or 1 score) |
| Proof it's neither impossible nor trivial | the two proofs (below) |

This is why you can't just "submit some code." Code with no question, no answer
key, and no grader is not an exam — it's a fragment. **A complete task is all
four parts together.**

## 4. The two proofs (the heart of "done")

Your task is only finished when both of these are true in a freshly built
container:

- **Empty run scores 0** — with no solution installed, the grader fails. This
  proves the problem is genuinely unsolved to begin with.
- **Your answer key scores 1** — after running your solution, the grader passes.
  This proves the task is solvable and your grader is correct.

If you remember nothing else, remember: **0 without the solution, 1 with it.**
That is the definition of a working exam. `SUBMISSION_HANDBOOK.md` shows the
exact commands.

## 5. The task in one paragraph (details in CANDIDATE_GUIDE.md)

A firmware code-signing key was rotated. Since then, release bundles signed with
the old (revoked) key are rejected by the distribution gateway with
`UNTRUSTED_SIGNATURE`. The **publisher** program that should reconcile the build
manifest, sign each release bundle with the *current* key, submit it to the
gateway, and record what it published — does not exist. As the examiner, you
first build that publisher (your answer key), then finish the exam around it.

## 6. The end-to-end process (your journey)

Work in this order. Each step depends on the one before it.

1. **Understand** — read all three docs and the gateway's README; run the
   provided service and poke it so you know how it behaves.
2. **Solve it yourself** — write the reference solution
   (`solution/publish.sh`) until your answer key makes the grader score **1**.
   You cannot write a fair question for a problem you haven't solved.
3. **Write the question** — turn your understanding into `instruction.md`: a
   precise brief that says exactly *what* to build and *where* (absolute paths,
   every rule, the success condition) but never *how* to solve it.
4. **Make it fair and hard** — add documented traps in the data that punish
   sloppy implementations; make sure every rule you grade is stated in the
   instructions, and that no one can cheat (edit the data, hardcode outputs,
   bypass checks).
5. **Prove both directions** — empty run → 0, your solution → 1, in a clean
   container. Paste both results into `AUTHOR_NOTES.md`.
6. **Package & submit** — clean the folder of junk, zip from the terminal, send
   it. `SUBMISSION_HANDBOOK.md` has the exact steps.

## 7. What we're judging (so you know what "good" is)

- **Solvable & verified** — your answer key scores 1; the empty run scores 0.
- **Clear & unambiguous** — a stranger could understand exactly what's required.
- **Genuinely challenging** — hard for an AI, fair for a human.
- **Cheat-resistant** — no shortcut to a passing score without doing the work.
- **Honest authorship** — see the next point.

## 8. Two rules that will end your assessment if broken

- **Everything you submit must be written by you.** Use AI to *learn* (explain a
  concept, decode an error), never to *generate* your instructions, solution, or
  tests. AI-generated submissions are rejected — and you will be asked to explain
  any line of your work in a live interview. If you can't explain it, it fails.
- **Don't modify the provided gateway service.** Talk to it over HTTP only; its
  private data store is off-limits.

## 9. You're ready when...
