#!/usr/bin/env node
'use strict';

import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import duckdbPkg from 'duckdb';

const { Database } = duckdbPkg;

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.join(__dirname, '..');

const CSV_PATH = path.join(ROOT_DIR, 'fixtures', 'build_manifest.csv');
const DB_PATH = path.join(ROOT_DIR, 'releases.duckdb');
const CURRENT_KEY_PATH = path.join(ROOT_DIR, 'keys', 'current', 'current.key.pem');
const CURRENT_CERT_PATH = path.join(ROOT_DIR, 'keys', 'current', 'current.cert.pem');
const GATEWAY_BASE_URL = process.env.GATEWAY_BASE_URL || 'http://127.0.0.1:7070';

function runAsync(con, sql, ...params) {
  return new Promise((resolve, reject) => {
    con.run(sql, ...params, (err) => (err ? reject(err) : resolve()));
  });
}

function allAsync(con, sql, ...params) {
  return new Promise((resolve, reject) => {
    con.all(sql, ...params, (err, rows) => (err ? reject(err) : resolve(rows)));
  });
}

function closeAsync(closable) {
  return new Promise((resolve, reject) => {
    closable.close((err) => (err ? reject(err) : resolve()));
  });
}

// UTF-8 JSON, keys sorted lexicographically, no insignificant whitespace — must
// match the gateway's canonicalization exactly or the signature won't verify.
function canonicalDescriptor(bundleId, artifactCount, totalBytes) {
  return JSON.stringify({
    artifact_count: artifactCount,
    bundle_id: bundleId,
    total_bytes: totalBytes,
  });
}

function signDescriptor(descriptorBytes) {
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'fw-sign-'));
  const contentFile = path.join(scratch, 'descriptor.bin');
  try {
    fs.writeFileSync(contentFile, descriptorBytes);
    return execFileSync(
      'openssl',
      [
        'cms', '-sign',
        '-in', contentFile,
        '-signer', CURRENT_CERT_PATH,
        '-inkey', CURRENT_KEY_PATH,
        '-md', 'sha256',
        '-outform', 'PEM',
        '-binary',
      ],
      { encoding: 'utf8' }
    );
  } finally {
    fs.rmSync(scratch, { recursive: true, force: true });
  }
}

async function fetchCurrentSigningKey() {
  const res = await fetch(`${GATEWAY_BASE_URL}/v1/signing-key/current`);
  if (!res.ok) {
    throw new Error(`GET /v1/signing-key/current failed with status ${res.status}`);
  }
  return res.json();
}

async function submitPublication(descriptor, signature, requestToken) {
  const res = await fetch(`${GATEWAY_BASE_URL}/v1/publications`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ descriptor, signature, request_token: requestToken }),
  });
  const body = await res.json();
  if (!res.ok || body.error) {
    throw new Error(
      `publication rejected for token ${requestToken}: ${body.error || res.status}`
    );
  }
  return body;
}

async function reconcilePublishableBundles(con) {
  const csvPathSql = CSV_PATH.replace(/\\/g, '/').replace(/'/g, "''");

  // Collapse exact-duplicate rows (identical across every column) on ingest.
  await runAsync(
    con,
    `CREATE OR REPLACE TABLE raw_manifest AS
     SELECT DISTINCT * FROM read_csv_auto('${csvPathSql}', header=true);`
  );

  // A bundle is publishable if it has at least one BUILD entry not cancelled by
  // a WITHDRAWAL that references it via supersedes_id.
  return allAsync(
    con,
    `SELECT bundle_id,
            COUNT(*) AS artifact_count,
            SUM(size_bytes) AS total_bytes
     FROM raw_manifest
     WHERE record_type = 'BUILD'
       AND entry_id NOT IN (
         SELECT DISTINCT supersedes_id
         FROM raw_manifest
         WHERE record_type = 'WITHDRAWAL'
           AND supersedes_id IS NOT NULL
           AND supersedes_id <> ''
       )
     GROUP BY bundle_id
     ORDER BY bundle_id;`
  );
}

async function ensurePublicationState(con) {
  await runAsync(
    con,
    `CREATE TABLE IF NOT EXISTS publication_state (
       bundle_id TEXT PRIMARY KEY,
       artifact_count BIGINT,
       total_bytes BIGINT,
       descriptor TEXT,
       key_id TEXT,
       request_token TEXT,
       publication_id TEXT,
       status TEXT,
       published_at TIMESTAMP DEFAULT current_timestamp
     );`
  );
}

async function main() {
  const db = new Database(DB_PATH);
  const con = db.connect();

  await ensurePublicationState(con);
  const bundles = await reconcilePublishableBundles(con);
  const signingKey = await fetchCurrentSigningKey();

  for (const row of bundles) {
    const bundleId = row.bundle_id;
    const artifactCount = Number(row.artifact_count);
    const totalBytes = Number(row.total_bytes);

    const existing = await allAsync(
      con,
      'SELECT key_id, request_token, publication_id, status FROM publication_state WHERE bundle_id = ?',
      bundleId
    );

    let keyId, requestToken, publicationId, status;

    if (existing.length > 0) {
      // Already published in a prior run: reuse the stored receipt instead of
      // re-signing/re-submitting, so a re-run cannot double-publish.
      ({ key_id: keyId, request_token: requestToken, publication_id: publicationId, status } =
        existing[0]);
    } else {
      const descriptor = canonicalDescriptor(bundleId, artifactCount, totalBytes);
      const signature = signDescriptor(Buffer.from(descriptor, 'utf8'));
      requestToken = `token-${bundleId}`;

      const receipt = await submitPublication(descriptor, signature, requestToken);
      keyId = signingKey.key_id;
      publicationId = receipt.publication_id;
      status = receipt.status;

      await runAsync(
        con,
        `INSERT INTO publication_state
           (bundle_id, artifact_count, total_bytes, descriptor, key_id, request_token, publication_id, status)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
        bundleId,
        artifactCount,
        totalBytes,
        descriptor,
        keyId,
        requestToken,
        publicationId,
        status
      );
    }

    console.log(`BUNDLE ${bundleId} SIGNED KEY=${keyId}`);
    console.log(
      `BUNDLE ${bundleId} PUBLISHED RECEIPT=${publicationId} TOKEN=${requestToken} STATUS=${status}`
    );
  }

  await closeAsync(con);
  await closeAsync(db);
}

if (process.argv.includes('--report')) {
  main().catch((err) => {
    console.error(err);
    process.exitCode = 1;
  });
}
