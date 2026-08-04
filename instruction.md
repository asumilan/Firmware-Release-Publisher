# Firmware Release Publisher

Release engineering rotated the firmware **code-signing key**. Since the rotation,
every release bundle the old publisher submits to the distribution gateway is
rejected with `UNTRUSTED_SIGNATURE`, because bundles are still signed with the
now-revoked key.

Implement `publisher/release-publisher.mjs` (Node 20, ESM) so that running:

```
npm run report        # = node publisher/release-publisher.mjs --report
```

does all of the following, in order:

1. Loads `fixtures/build_manifest.csv` into an embedded DuckDB database at
   `releases.duckdb` (created at run time — do not pre-create it).
2. Uses SQL to reconcile the manifest into the set of **publishable bundles**
   (rules below).
3. For each publishable bundle, fetches the current signing key from the
   distribution gateway, builds a canonical release descriptor, signs it with
   OpenSSL detached CMS using the **current** keypair, and submits it to the
   gateway over HTTP.
4. Persists each gateway receipt and request token in `releases.duckdb` so a
   re-run does not double-publish.
5. Prints deterministic status lines, in ascending `bundle_id` order, that
   reproduce `reports/publications.expected.txt` (the grader masks only the
   random `RECEIPT` value).

## Environment

Everything lives under `/app`:

| Path | What it is |
| --- | --- |
| `fixtures/build_manifest.csv` | The raw input to reconcile. |
| `reports/publications.expected.txt` | Golden output your program must reproduce. |
| `package.json` | Defines `npm run report` and pins the `duckdb` dependency. |
| `distribution-gateway/` | The provided Express service. Do not modify it. |
| `keys/current/current.{key,cert}.pem` | The signing keypair currently in force. |
| `keys/revoked/revoked.{key,cert}.pem` | The retired keypair. Signing with it fails — do not use it. |
| `publisher/` | Empty. `release-publisher.mjs` goes here. |

## Manifest schema

```
entry_id,bundle_id,component_id,version,size_bytes,record_type,supersedes_id,recorded_at
```

`record_type` is `BUILD` or `WITHDRAWAL`. A `WITHDRAWAL` row's `supersedes_id` is
the `entry_id` of the `BUILD` row it cancels.

## Reconciliation rules (binding)

Derive publishable bundles with SQL, applying these rules in order:

1. **Collapse exact duplicates.** A row is a duplicate only if it is identical to
   another row across **every column**. Collapse each such set to a single row.
   Rows that merely share a `bundle_id` or `component_id` are not duplicates.
2. **Apply withdrawals.** A `BUILD` row is cancelled if its `entry_id` equals the
   `supersedes_id` of any (post-collapse) `WITHDRAWAL` row. No other matching
   (size, version, etc.) is required or should be checked.
3. A bundle is **publishable** if at least one of its `BUILD` rows survives steps
   1–2. A bundle whose every build was withdrawn or was itself a withdrawn
   duplicate is omitted from the output entirely.

Only bundle **membership** (which `bundle_id`s are publishable) is graded. The
exact per-bundle `artifact_count` / `total_bytes` you put in the signed
descriptor is not independently re-derived by the grader — compute it from
whatever surviving rows you keep after steps 1–2, consistently.

## Gateway contract

Base URL `http://127.0.0.1:7070`.

- `GET /v1/signing-key/current` → `{ key_id, algorithm, certificate_ref, status }`.
  Use the returned `key_id` in your `SIGNED KEY=` status line.
- `POST /v1/publications` with `{ descriptor, signature, request_token }` →
  `{ publication_id, request_token, status: "PUBLISHED" }` on success, or
  `{ error: "UNTRUSTED_SIGNATURE" }` if the signature doesn't verify against the
  current certificate. Re-posting the same `request_token` replays the original
  receipt (no duplicate is created).

Use the deterministic token `token-<bundle_id>` as `request_token`.

## Canonical descriptor and signing (binding)

The descriptor you sign is:

```json
{"artifact_count":<int>,"bundle_id":"<bundle_id>","total_bytes":<int>}
```

encoded as UTF-8 JSON with object keys in lexicographic order and **no
insignificant whitespace** (e.g. `JSON.stringify` with keys inserted in sorted
order — `artifact_count`, `bundle_id`, `total_bytes`). The bytes you sign must be
byte-for-byte identical to the bytes you send as `descriptor`, or verification
fails.

Sign with detached CMS, SHA-256 digest, PEM output, using the **current**
keypair:

```
openssl cms -sign -in <descriptor-bytes-file> \
  -signer keys/current/current.cert.pem \
  -inkey  keys/current/current.key.pem \
  -md sha256 -outform PEM -binary
```

## Persistence (binding schema)

`releases.duckdb` must contain a table named `publication_state` with at least
these columns:

| Column | Meaning |
| --- | --- |
| `bundle_id` | The published bundle's id. |
| `request_token` | The token used for that bundle (`token-<bundle_id>`). |
| `publication_id` | The gateway's receipt id for that bundle. |
| `status` | The gateway's returned status (`PUBLISHED`). |

Additional columns are allowed. One row per publishable bundle. On a re-run,
reuse the stored row instead of re-signing/re-submitting.

## Output format (binding)

For each publishable bundle, in ascending `bundle_id` order, print exactly two
lines:

```
BUNDLE <bundle_id> SIGNED KEY=<key_id>
BUNDLE <bundle_id> PUBLISHED RECEIPT=<publication_id> TOKEN=<request_token> STATUS=<status>
```

`<key_id>` comes from `GET /v1/signing-key/current`.

## Boundaries

- Interact with the gateway **only** over HTTP. Do not read or write
  `distribution-gateway/data/gateway.json` directly.
- Do not disable, mock, or bypass signature verification.
- Do not sign with the revoked key.
- Do not hardcode the golden output, receipt ids, or row counts — derive
  everything from the manifest and the gateway's live responses.
- Keep output ordering deterministic (sort by `bundle_id`).

## Definition of done

- `npm run report` reproduces `reports/publications.expected.txt` (receipt
  masked), in bundle-id order.
- The publishable-bundle set matches the reconciliation rules above.
- Every submission is `PUBLISHED` — none is `UNTRUSTED_SIGNATURE`.
- `releases.duckdb` contains `publication_state` populated per bundle.
- Re-running produces identical stdout and does not create duplicate
  publications on the gateway.
