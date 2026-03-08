#!/bin/bash
#
# Run the Claude agent via Harbor, extract the mission plan, and visualize it.
#
# This script:
# 1. Runs the ClaudeAgent via Harbor with artifact extraction enabled
# 2. Finds the extracted mission_plan.json from the job artifacts
# 3. Converts it to the visualizer's format
# 4. Copies it to the mission-visualizer
# 5. Builds and launches the visualizer
#
# Prerequisites:
#   - Python virtualenv "skillathon" with harbor + anthropic installed
#   - ANTHROPIC_API_KEY in .env.local
#   - Docker running (Harbor uses it for the task environment)
#   - Node.js + npm (for the visualizer)
#
# Usage:
#   ./run-agent-visualize.sh [OPTIONS]
#
# Options:
#   --job-name NAME   Custom job name (default: agent-viz-<timestamp>)
#   --open            Open browser automatically after starting visualizer
#   --model MODEL     Model to use (default: anthropic/claude-sonnet-4-20250514)
#   --skip-agent      Skip agent run, use latest existing job artifacts
#   --debug           Enable Harbor debug logging
#   --help            Show this help message

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VISUALIZER_DIR="$SCRIPT_DIR/mission-visualizer"
ENV_FILE="$SCRIPT_DIR/.env.local"

# Defaults
JOB_NAME="agent-viz-$(date +%Y%m%d-%H%M%S)"
OPEN_BROWSER=false
MODEL="anthropic/claude-sonnet-4-20250514"
SKIP_AGENT=false
DEBUG_FLAG=""

# Parse args
for arg in "$@"; do
    case $arg in
        --open) OPEN_BROWSER=true ;;
        --skip-agent) SKIP_AGENT=true ;;
        --debug) DEBUG_FLAG="--debug" ;;
        --help)
            head -25 "$0" | tail -20
            exit 0
            ;;
        --job-name=*) JOB_NAME="${arg#*=}" ;;
        --model=*) MODEL="${arg#*=}" ;;
    esac
done

echo "=== Agent → Visualize Pipeline ==="
echo ""

# ── Step 0: Load API key ──────────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
    export ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY "$ENV_FILE" | cut -d= -f2)
fi

if [[ -z "$ANTHROPIC_API_KEY" ]]; then
    echo "ERROR: ANTHROPIC_API_KEY not set. Add it to .env.local or export it."
    exit 1
fi

# ── Step 1: Run agent via Harbor ──────────────────────────────────────
JOBS_DIR="$SCRIPT_DIR/jobs"
JOB_DIR="$JOBS_DIR/$JOB_NAME"

if $SKIP_AGENT; then
    echo "[1/4] Skipping agent run (--skip-agent), finding latest job..."
    # Find the most recent job directory
    JOB_DIR=$(ls -dt "$JOBS_DIR"/*/ 2>/dev/null | head -1)
    if [[ -z "$JOB_DIR" ]]; then
        echo "ERROR: No existing jobs found in $JOBS_DIR"
        exit 1
    fi
    JOB_DIR="${JOB_DIR%/}"
    JOB_NAME=$(basename "$JOB_DIR")
    echo "  Using job: $JOB_NAME"
else
    echo "[1/4] Running ClaudeAgent via Harbor..."
    echo "  Job: $JOB_NAME"
    echo "  Model: $MODEL"
    echo "  This may take 2-3 minutes..."
    echo ""

    # Activate virtualenv and run Harbor with artifact extraction
    source ~/.virtualenvs/skillathon/bin/activate

    PYTHONPATH="$SCRIPT_DIR" harbor run \
        -p "$SCRIPT_DIR/task/" \
        --agent-import-path agent.claude_agent:ClaudeAgent \
        -m "$MODEL" \
        --job-name "$JOB_NAME" \
        --artifact /app/mission_plan.json \
        $DEBUG_FLAG

    echo ""
    echo "  Agent run complete."
fi

# ── Step 2: Extract mission plan from artifacts ───────────────────────
echo "[2/4] Extracting mission plan from job artifacts..."

# Find the trial directory (Harbor creates task__<random> subdirs)
TRIAL_DIR=$(ls -d "$JOB_DIR"/task__*/ 2>/dev/null | head -1)
if [[ -z "$TRIAL_DIR" ]]; then
    echo "ERROR: No trial directory found in $JOB_DIR"
    exit 1
fi
TRIAL_DIR="${TRIAL_DIR%/}"
TRIAL_NAME=$(basename "$TRIAL_DIR")

# Look for the artifact
ARTIFACT_PATH="$TRIAL_DIR/artifacts/mission_plan.json"
if [[ ! -f "$ARTIFACT_PATH" ]]; then
    # Try alternate locations Harbor might place it
    ARTIFACT_PATH=$(find "$TRIAL_DIR/artifacts" -name "mission_plan.json" 2>/dev/null | head -1)
fi

if [[ -z "$ARTIFACT_PATH" || ! -f "$ARTIFACT_PATH" ]]; then
    echo "ERROR: mission_plan.json not found in artifacts."
    echo "  Looked in: $TRIAL_DIR/artifacts/"
    echo "  The agent may not have produced /app/mission_plan.json."
    echo ""
    echo "  Verifier output:"
    cat "$TRIAL_DIR/verifier/test-stdout.txt" 2>/dev/null || echo "  (no verifier output)"
    exit 1
fi

echo "  Found: $ARTIFACT_PATH"

# Show reward
REWARD=$(cat "$TRIAL_DIR/verifier/reward.txt" 2>/dev/null || echo "unknown")
echo "  Reward: $REWARD"

# ── Step 3: Convert to visualizer format ──────────────────────────────
echo "[3/4] Converting mission plan to visualizer format..."

VISUALIZER_JSON="$VISUALIZER_DIR/src/data/generatedMission.json"

# Activate virtualenv for Python conversion
source ~/.virtualenvs/skillathon/bin/activate 2>/dev/null || true

python3 -c "
import json, sys, math

with open('$ARTIFACT_PATH', 'r') as f:
    plan = json.load(f)

AU_KM = 149_597_870.7
mu_sun = 1.327124400189e11  # km^3/s^2

# Extract core fields
mission_name = plan.get('mission_name', 'Agent Mission')
departure_date = plan.get('departure_date', '')
total_dv = plan.get('total_delta_v_km_s', 0)
max_dist = plan.get('max_distance_AU', 0)

# Duration
dep_date = plan.get('departure_date', '')
ret_date = plan.get('return_date', '')
duration = plan.get('verification', {}).get('mission_duration_days', 0)
if not duration and dep_date and ret_date:
    from datetime import datetime
    d1 = datetime.strptime(dep_date, '%Y-%m-%d')
    d2 = datetime.strptime(ret_date, '%Y-%m-%d')
    duration = (d2 - d1).days

# Tier
if max_dist >= 6.0:
    tier = 'Platinum'
elif max_dist >= 4.0:
    tier = 'Gold'
elif max_dist >= 2.0:
    tier = 'Silver'
else:
    tier = 'Bronze'

# Build delta-v breakdown
dv_breakdown = {}
for phase in plan.get('phases', []):
    dv_breakdown[phase.get('phase', 'unknown')] = phase.get('delta_v_km_s', 0)

# Convert phases to visualizer format
viz_phases = []
for phase in plan.get('phases', []):
    orbit = None
    transfer = phase.get('transfer_orbit') or phase.get('post_flyby_orbit')
    if transfer:
        a_km = transfer.get('a_km', 0)
        e = transfer.get('e', 0)
        if a_km > 0:
            a_au = a_km / AU_KM
            period_s = 2 * math.pi * math.sqrt(a_km**3 / mu_sun)
            period_days = period_s / 86400
            orbit = {
                'a_AU': round(a_au, 4),
                'e': round(e, 6),
                'omega_rad': transfer.get('omega_rad', 0),
                'period_days': round(period_days)
            }

    viz_phase = {
        'phase': phase.get('phase', ''),
        'date': phase.get('date', ''),
        'delta_v_km_s': phase.get('delta_v_km_s', 0),
        'orbit': orbit,
        'description': phase.get('maneuver', phase.get('phase', ''))
    }
    viz_phases.append(viz_phase)

# Build flybys array
flybys = []
for phase in plan.get('phases', []):
    if phase.get('phase') == 'flyby':
        flybys.append({
            'planet': phase.get('body', ''),
            'date': phase.get('date', ''),
            'periapsis_altitude_km': phase.get('periapsis_km', 0),
            'turn_angle_deg': phase.get('turn_angle_deg', 0),
            'incoming_v_inf_km_s': 0,
            'outgoing_v_inf_km_s': 0
        })

viz_plan = {
    'mission_name': mission_name,
    'departure_date': departure_date,
    'total_delta_v_km_s': total_dv,
    'max_distance_AU': max_dist,
    'mission_duration_days': duration,
    'tier': tier,
    'verification': {
        'mission_duration_days': duration,
        'delta_v_breakdown_km_s': dv_breakdown
    },
    'phases': viz_phases,
    'flybys': flybys
}

with open('$VISUALIZER_JSON', 'w') as f:
    json.dump(viz_plan, f, indent=2)

print(f'  Mission: {mission_name}')
print(f'  Tier: {tier} | Distance: {max_dist:.3f} AU | Delta-v: {total_dv:.3f} km/s | Duration: {duration} days')
"

echo "  Written to: src/data/generatedMission.json"

# ── Step 4: Build and launch visualizer ───────────────────────────────
echo "[4/4] Launching mission visualizer..."
cd "$VISUALIZER_DIR"

# Install deps if needed
if [[ ! -d "node_modules" ]]; then
    echo "  Installing dependencies..."
    npm install --silent
fi

# Build for preview (faster than dev server for one-shot viewing)
echo "  Building..."
npm run build --silent

# Kill any existing preview server
pkill -f "vite preview" 2>/dev/null || true
sleep 1

echo ""
echo "=== Mission Visualizer Ready ==="
echo "  Job: $JOB_NAME (trial: $TRIAL_NAME)"
echo "  Reward: $REWARD"
echo ""
echo "Starting preview server on http://localhost:4173"
echo "  - Generated mission: http://localhost:4173/?mission=generated"
echo "  - Sample mission:    http://localhost:4173/?mission=sample"
echo ""

if $OPEN_BROWSER; then
    npx vite preview --port 4173 &
    sleep 2
    open "http://localhost:4173/?mission=generated"
    wait
else
    npx vite preview --port 4173
fi
