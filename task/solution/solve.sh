#!/bin/bash
# Oracle solution for Deep Space Explorer task.
# Computes a Lambert-optimized Earth-Mars-Earth round trip.
# Produces /app/mission_plan.json for the verifier.

set -e

echo "=== Running Oracle Solution ==="

SCRIPT_DIR="$(dirname "$0")"
python3 "${SCRIPT_DIR}/solve.py"

echo ""
echo "=== Oracle solution complete ==="
