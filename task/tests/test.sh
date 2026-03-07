#!/bin/bash
# Verification script for Deep Space Explorer task.
# Called by Harbor after the agent finishes.
# Reads /app/mission_plan.json, verifies constraints, writes reward to /logs/verifier/reward.txt.

set -e

mkdir -p /logs/verifier

echo "=== Deep Space Explorer Verifier ==="
echo ""

# Run the Python verification script
# test.sh is copied to /tests/ at runtime; verify_mission.py is alongside it
SCRIPT_DIR="$(dirname "$0")"
python3 "${SCRIPT_DIR}/verify_mission.py"

# verify_mission.py writes the reward file directly
echo ""
echo "=== Verification complete ==="
