#!/bin/bash

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    exit 1
fi

mkdir -p /logs/verifier

# Reset state left over from a prior grading pass in this container so a re-run
# (e.g. negative-control then solution) starts clean.
rm -f releases.duckdb releases.duckdb.wal
rm -f distribution-gateway/data/gateway.json

# Launch the provided distribution gateway in the background on its fixed port and
# wait for it to accept connections before driving any assertions against it.
(cd distribution-gateway && exec node server.js) > /logs/verifier/gateway.log 2>&1 &
GATEWAY_PID=$!
trap 'kill "$GATEWAY_PID" 2>/dev/null' EXIT

ready=0
for _ in $(seq 1 50); do
  if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7070/healthz', timeout=1)" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.2
done

if [ "$ready" -ne 1 ]; then
  echo "Error: distribution-gateway did not become ready on port 7070." >&2
  cat /logs/verifier/gateway.log >&2
  echo 0 > /logs/verifier/reward.txt
  exit 1
fi

# pytest + pytest-json-ctrf are pre-installed in the verifier image (shared mode).
# allow_internet=false, so no wheels are resolved at run time — invoke pytest directly.
python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
code=$?

# Surface pytest's raw exit code so the negative-control check can tell "tests ran
# and failed" (code 1, expected with no solution) from "tests could not run" (>=2).
echo "pytest exit code: ${code}"

if [ "$code" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
