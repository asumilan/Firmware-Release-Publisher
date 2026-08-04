# Author Notes

## What changed in this pass

- **`instruction.md`** — was the unedited scaffold placeholder ("Placeholder
  instruction — Scaffold harbor_negative_control stub..."). Replaced with the
  real, binding candidate-facing spec, derived from `CANDIDATE_GUIDE.md` and
  `completion_plan.md`. Both open questions from `completion_plan.md` /
  `scaffold_plan.yaml` are resolved explicitly:
  - Duplicate rows: identical **across every column**, nothing looser.
  - Withdrawal rule: a `WITHDRAWAL` cancels the `BUILD` whose `entry_id` equals
    its `supersedes_id`; no other field matching required.
  Also pins the `publication_state` DuckDB schema (`bundle_id`, `request_token`,
  `publication_id`, `status`) so the verifier can check persistence without
  over-constraining implementation details the guide left open.

- **`solution/publish.sh`** — was a no-op `exit 0` stub. Now deploys the
  reference implementation to `publisher/release-publisher.mjs`, the one file a
  correct submission delivers.

- **`solution/release-publisher.mjs`** — relocated here from
  `environment/publisher/release-publisher.mjs` (added in a prior commit,
  "solution", by a different author). It was sitting in the wrong place: per
  `_originality_note.md` / `scaffold_plan.yaml`, `publisher/` in the shipped
  environment must stay empty (it's the candidate's deliverable). It was never
  actually leaked to candidates — `environment/Dockerfile` only `COPY`s
  `distribution-gateway/`, `fixtures/`, `reports/`, and the root
  `package.json`, so `environment/publisher/` was never part of the built
  image — but leaving a correct reference solution inside `environment/` was
  fragile and wrong on principle. Moved to `solution/`, `environment/publisher/`
  is empty again.

- **`tests/test_outputs.py`** — this was the most serious gap, not mentioned in
  the original review: the file contained a complete, unrelated test suite for
  a different scaffold ("RiftArena cartridge-decode repair" text adventure —
  wrong domain entirely, imported `riftarena.playthrough`). It could never have
  passed against this task. Rewritten from scratch against the real task, one
  test per `functional_criteria[]` entry in `scaffold_plan.yaml`:
  - golden-output diff (RECEIPT masked),
  - independent recomputation of the publishable-bundle set straight from the
    raw CSV (not trusting the candidate's SQL),
  - accept-with-current / reject-with-revoked driven directly against the live
    gateway with verifier-owned signatures (independent of the candidate's own
    requests),
  - DuckDB persistence check against the schema pinned in `instruction.md`,
  - re-run idempotency (identical stdout, no duplicate gateway publications).
  One test is `@pytest.mark.skip`, matching the deferred "exact per-group
  totals" sub-question documented in `_skeleton.md` / `completion_plan.md` —
  only bundle-membership is graded, by design.

- **`tests/test.sh`** — previously only ran pytest; nothing started the
  distribution gateway the tests (and the candidate's own `npm run report`)
  depend on. Now resets any leftover `releases.duckdb` / gateway ledger state,
  starts `distribution-gateway` in the background, polls `/healthz` (via
  `python3 -c` — no `curl` in the image) before running pytest, and tears the
  gateway down on exit.

- Removed a stray empty junk directory, `environment/publisher;C`, left over
  from an earlier shell mistake.

## Verification

Both proofs were run in a freshly built Docker image (`environment/Dockerfile`),
each in its own `docker run` container (no state carried between them):

- **Empty submission** (no `solution/publish.sh` applied, `publisher/` absent):
  `npm run report` fails with `MODULE_NOT_FOUND`, pytest fails on the first
  test that shells out to it, `tests/test.sh` writes `reward.txt = 0`.
- **Reference solution applied** (`bash solution/publish.sh` run from `/app`
  first): all non-skipped tests pass, `tests/test.sh` writes `reward.txt = 1`.

See the session transcript for the exact `docker build` / `docker run`
invocations and captured output.

## Known limitations / deliberate scope cuts

- Per design, exact per-bundle `artifact_count` / `total_bytes` in the signed
  descriptor is not independently re-verified — only bundle membership is
  graded (see `test_exact_per_bundle_totals_match_reconciliation`, skipped).
- `distribution-gateway/` itself was already correct and complete when this
  pass started; not modified beyond confirming its own `node --test` suite
  still passes.
