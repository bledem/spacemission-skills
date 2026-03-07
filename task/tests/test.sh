#!/bin/bash
# Test script — verifies the agent completed the task.
# Must produce a reward file at /logs/verifier/reward.txt

mkdir -p /logs/verifier

# Example: run pytest and write reward based on exit code
# uvx pytest /tests/test.py

# Placeholder — replace with your actual verification logic
if true; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
