"""Verifier tests for the firmware release publisher task.

Each test maps to a functional_criteria[] entry (see scaffold_plan.yaml). Run via
tests/test.sh, which resets state, launches the provided distribution-gateway in
the background on port 7070, and writes /logs/verifier/reward.txt.

Assumes cwd is the task workdir (/app): fixtures/, reports/, keys/, and
distribution-gateway/ all live directly under it, matching instruction.md.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import tempfile
from pathlib import Path

import duckdb
import pytest
import requests

APP_DIR = Path.cwd()
CSV_PATH = APP_DIR / "fixtures" / "build_manifest.csv"
GOLDEN_PATH = APP_DIR / "reports" / "publications.expected.txt"
DB_PATH = APP_DIR / "releases.duckdb"
GATEWAY_LEDGER_PATH = APP_DIR / "distribution-gateway" / "data" / "gateway.json"
CURRENT_CERT = APP_DIR / "keys" / "current" / "current.cert.pem"
CURRENT_KEY = APP_DIR / "keys" / "current" / "current.key.pem"
REVOKED_CERT = APP_DIR / "keys" / "revoked" / "revoked.cert.pem"
REVOKED_KEY = APP_DIR / "keys" / "revoked" / "revoked.key.pem"
GATEWAY_BASE_URL = "http://127.0.0.1:7070"

RECEIPT_RE = re.compile(r"RECEIPT=\S+")


def mask(text: str) -> str:
    return RECEIPT_RE.sub("RECEIPT=<masked>", text)


def run_report() -> str:
    result = subprocess.run(
        ["npm", "run", "--silent", "report"],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"npm run report exited {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result.stdout


def expected_bundle_ids() -> list[str]:
    """Independently recompute the publishable-bundle set straight from the raw
    CSV, per the reconciliation rules pinned in instruction.md: collapse rows
    identical across every column, drop BUILD rows referenced by a WITHDRAWAL's
    supersedes_id, and keep bundles with at least one surviving BUILD. Only the
    group-membership invariant is graded (see instruction.md open questions)."""
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    seen = set()
    unique_rows = []
    for row in rows:
        key = tuple(row.items())
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)

    withdrawn_entry_ids = {
        row["supersedes_id"]
        for row in unique_rows
        if row["record_type"] == "WITHDRAWAL" and row.get("supersedes_id")
    }

    surviving_by_bundle: dict[str, int] = {}
    for row in unique_rows:
        if row["record_type"] != "BUILD" or row["entry_id"] in withdrawn_entry_ids:
            continue
        surviving_by_bundle[row["bundle_id"]] = surviving_by_bundle.get(row["bundle_id"], 0) + 1

    return sorted(bundle for bundle, count in surviving_by_bundle.items() if count > 0)


def sign_detached(cert_path: Path, key_path: Path, payload: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".bin") as content_file:
        content_file.write(payload)
        content_file.flush()
        result = subprocess.run(
            [
                "openssl", "cms", "-sign",
                "-in", content_file.name,
                "-signer", str(cert_path),
                "-inkey", str(key_path),
                "-md", "sha256",
                "-outform", "PEM",
                "-binary",
            ],
            capture_output=True,
            timeout=30,
        )
    assert result.returncode == 0, result.stderr.decode()
    return result.stdout.decode()


@pytest.fixture(scope="module")
def report_output() -> str:
    return run_report()


def test_report_output_matches_golden(report_output):
    """functional_criteria[id=report_output_matches]"""
    golden = GOLDEN_PATH.read_text(encoding="utf-8")
    assert mask(report_output.strip()) == mask(golden.strip())


def test_withdrawals_and_duplicates_reconciled(report_output):
    """functional_criteria[id=withdrawals_and_duplicates_reconciled]"""
    published_bundle_ids = sorted(set(re.findall(r"BUNDLE (\S+) SIGNED", report_output)))
    assert published_bundle_ids == expected_bundle_ids()


@pytest.mark.skip(
    reason="Open question (instruction.md): exact per-bundle artifact_count/total_bytes "
    "depends on which duplicate-collapse interpretation is used for the signed descriptor "
    "payload itself; only the group-membership invariant above is graded."
)
def test_exact_per_bundle_totals_match_reconciliation():
    raise NotImplementedError


def test_bundles_signed_with_current_key_accepted(report_output):
    """functional_criteria[id=bundles_signed_with_current_key_accepted]"""
    assert "UNTRUSTED_SIGNATURE" not in report_output
    statuses = re.findall(r"STATUS=(\S+)", report_output)
    assert statuses, "no PUBLISHED status lines found in report output"
    assert all(status == "PUBLISHED" for status in statuses)


def test_receipts_and_tokens_persisted_in_duckdb(report_output):
    """functional_criteria[id=receipts_and_tokens_persisted_in_duckdb]"""
    assert DB_PATH.exists(), "releases.duckdb was not created"
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = con.execute(
            "SELECT bundle_id, request_token, publication_id, status FROM publication_state"
        ).fetchall()
    finally:
        con.close()

    persisted_bundle_ids = {row[0] for row in rows}
    assert persisted_bundle_ids == set(expected_bundle_ids())
    for bundle_id, request_token, publication_id, status in rows:
        assert request_token == f"token-{bundle_id}"
        assert publication_id
        assert status == "PUBLISHED"


def test_idempotent_rerun_no_duplicate_publications(report_output):
    """functional_criteria[id=idempotent_rerun_no_duplicate_publications]"""
    assert GATEWAY_LEDGER_PATH.exists(), "gateway ledger was not created by the first run"
    ledger_before = json.loads(GATEWAY_LEDGER_PATH.read_text(encoding="utf-8"))
    count_before = len(ledger_before.get("publications", {}))
    assert count_before == len(expected_bundle_ids())

    second_output = run_report()
    assert second_output.strip() == report_output.strip()

    ledger_after = json.loads(GATEWAY_LEDGER_PATH.read_text(encoding="utf-8"))
    assert len(ledger_after.get("publications", {})) == count_before


def test_revoked_key_signature_rejected():
    """functional_criteria[id=revoked_key_signature_rejected]

    Verifier-owned requests, independent of the candidate's own run: confirms the
    gateway itself still accepts a current-key signature and rejects a revoked-key
    signature, so a candidate cannot pass by disabling verification."""
    descriptor = json.dumps(
        {"artifact_count": 1, "bundle_id": "BND-VERIFIER-CHECK", "total_bytes": 1},
        sort_keys=True,
        separators=(",", ":"),
    )
    payload = descriptor.encode("utf-8")

    accepted_signature = sign_detached(CURRENT_CERT, CURRENT_KEY, payload)
    accept_response = requests.post(
        f"{GATEWAY_BASE_URL}/v1/publications",
        json={
            "descriptor": descriptor,
            "signature": accepted_signature,
            "request_token": "verifier-accept-check",
        },
        timeout=10,
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "PUBLISHED"

    rejected_signature = sign_detached(REVOKED_CERT, REVOKED_KEY, payload)
    reject_response = requests.post(
        f"{GATEWAY_BASE_URL}/v1/publications",
        json={
            "descriptor": descriptor,
            "signature": rejected_signature,
            "request_token": "verifier-reject-check",
        },
        timeout=10,
    )
    assert reject_response.status_code != 200
    assert reject_response.json()["error"] == "UNTRUSTED_SIGNATURE"
