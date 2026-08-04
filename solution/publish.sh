#!/bin/bash
# Reference solution entrypoint.
#
# Deploys the one file a correct submission delivers — publisher/release-publisher.mjs
# — into the task workdir, exactly where a candidate's own implementation would go
# (see instruction.md / CANDIDATE_GUIDE.md). Used by the grading harness to prove the
# task is solvable (reward 1) and to calibrate the empty-submission negative control
# (reward 0). Not part of the candidate-visible environment: excluded from the image
# build via environment/.dockerignore.
set -euo pipefail

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Run this from the task workdir (/app)." >&2
    exit 1
fi

SOLUTION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p publisher
cp "$SOLUTION_DIR/release-publisher.mjs" publisher/release-publisher.mjs
