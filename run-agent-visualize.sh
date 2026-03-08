#!/bin/bash
#
# Run the Claude agent via Harbor, extract the mission plan, and visualize it.
#
# New flow:
# 1. Open the visualizer in prompt mode — user enters mission objective in browser
# 2. Inject the captured objective into a temp copy of the task directory
# 3. Run the ClaudeAgent via Harbor (stdout tailed to SSE server for live feed)
# 4. Extract mission_plan.json from the job artifacts
# 5. Convert it to the visualizer's format
# 6. Build and launch the visualizer with the results
#
# Prerequisites:
#   - ANTHROPIC_API_KEY in .env.local
#   - Docker running (Harbor uses it for the task environment)
#   - Node.js + npm (for the visualizer)
#   - Python 3 (for the capture server)
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

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VISUALIZER_DIR="$SCRIPT_DIR/mission-visualizer"
INSTRUCTION_FILE="$SCRIPT_DIR/task/instruction.md"
ENV_FILE="$SCRIPT_DIR/.env.local"

CAPTURE_PORT=8788
VITE_PORT=5174

# Defaults
JOB_NAME="agent-viz-$(date +%Y%m%d-%H%M%S)"
OPEN_BROWSER=false
MODEL="anthropic/claude-sonnet-4-20250514"
SKIP_AGENT=false
DRY_RUN=false
DEBUG_FLAG=""

for arg in "$@"; do
    case $arg in
        --open)         OPEN_BROWSER=true ;;
        --skip-agent)   SKIP_AGENT=true ;;
        --dry-run)      DRY_RUN=true; SKIP_AGENT=true ;;
        --debug)        DEBUG_FLAG="--debug" ;;
        --help)         head -30 "$0" | tail -25; exit 0 ;;
        --job-name=*)   JOB_NAME="${arg#*=}" ;;
        --model=*)      MODEL="${arg#*=}" ;;
    esac
done

echo "=== Agent → Visualize Pipeline ==="
echo ""

# ── Step 0: Load API key ──────────────────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
    export ANTHROPIC_API_KEY
    ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY "$ENV_FILE" | cut -d= -f2)
fi
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "ERROR: ANTHROPIC_API_KEY not set. Add it to .env.local or export it."
    exit 1
fi

# ── Cleanup handler ───────────────────────────────────────────────────────────
CAPTURE_PID=""
VITE_PID=""
PROMPT_FILE="/tmp/mission_prompt_$$.json"
LOG_FILE="/tmp/agent_log_$$.txt"
HIGHLIGHT_PY="/tmp/skill_highlight_$$.py"
TASK_TMP_DIR=""

cleanup() {
    echo ""
    echo "  Cleaning up..."
    [[ -n "$CAPTURE_PID" ]] && kill "$CAPTURE_PID" 2>/dev/null || true
    [[ -n "$VITE_PID"    ]] && kill "$VITE_PID"    2>/dev/null || true
    rm -f "$PROMPT_FILE" "$LOG_FILE" "$HIGHLIGHT_PY"
    [[ -n "$TASK_TMP_DIR" ]] && rm -rf "$TASK_TMP_DIR"
    
    # Also clean up any lingering harbor containers if they cause issues
    docker ps -q --filter "name=task__" | xargs -r docker rm -f 2>/dev/null || true
}
trap cleanup EXIT

# Write the skill highlighter to a temp file so it can read from the pipeline's
# stdin (using python3 - <<HEREDOC conflicts: the heredoc consumes stdin,
# leaving nothing for sys.stdin to read from the pipe).
cat > "$HIGHLIGHT_PY" << 'PYEOF'
import sys, re

RESET = '\033[0m'
BOLD  = '\033[1m'
DIM   = '\033[2m'

def c(n): return f'\033[{n}m'

SKILLS = [
    (c('35'), 'Step 1 · Write script',   re.compile(r'\b(single script|one script|complete script|tee|cat\s*>)\b', re.I)),
    (c('36'), 'Step 2 · Δv from v∞',    re.compile(r'\b(dv_from_vinf|v_inf|vinf|mu_earth|mu_mars|mu_venus|dv_dep|dv_arr|dv_cap|parking.orbit)\b', re.I)),
    (c('34'), 'Step 3 · Lambert solver', re.compile(r'\b(lambert|solve_lambert|OrbitDetermination|set_celestial_body|heliocentric|transfer.orbit)\b', re.I)),
    (c('33'), 'Step 4 · Strategy',       re.compile(r'\b(strategy|gravity.assist|flyby|hohmann|bi.elliptic|Venus|Jupiter|Saturn|swing.by)\b', re.I)),
    (c('32'), 'Step 5 · Window scan',    re.compile(r'\b(ephemeris|synodic|departure.window|timedelta|departure.date)\b', re.I)),
    (c('31'), 'Step 6 · Mission plan',   re.compile(r'\b(mission_plan\.json|json\.dump|verif|all_constraints|reward)\b', re.I)),
]

TURN_RE    = re.compile(r'Turn\s+(\d+)/(\d+)')
THINK_RE   = re.compile(r'\[assistant\]\s*')
EXEC_RE    = re.compile(r'^Executing:\s*')
OUTPUT_RE  = re.compile(r'^Output:\s*')
DONE_RE    = re.compile(r'Agent finished', re.I)
SECTION_RE = re.compile(r'^(Turn |Executing:|Output:|Agent finished|INFO|WARNING|ERROR|\[)', re.I)

last_step   = None
in_thinking = False
in_output   = False

def highlight_keywords(text):
    for color, _, pat in SKILLS:
        text = pat.sub(lambda m, col=color: f'{col}{BOLD}{m.group()}{RESET}', text)
    return text

def skill_banner(color, label):
    bar = '─' * 58
    return f'\n{color}{BOLD}┌{bar}┐\n│  ◆ SKILL  {label:<46}│\n└{bar}┘{RESET}'

def check_skill(line):
    global last_step
    for color, label, pat in SKILLS:
        if pat.search(line):
            if label != last_step:
                last_step = label
                print(skill_banner(color, label), flush=True)
            break

try:
    for raw in sys.stdin:
        line = raw.rstrip('\n')
        if not line:
            print("", flush=True)
            continue

        m = TURN_RE.search(line)
        if m:
            in_thinking = in_output = False
            cur, total = int(m.group(1)), int(m.group(2))
            filled = int(cur / total * 32)
            bar = '█' * filled + '░' * (32 - filled)
            print(f'\n{BOLD}{c("37")}  ── Turn {cur}/{total}  [{bar}]{RESET}\n', flush=True)
            continue

        if DONE_RE.search(line):
            in_thinking = in_output = False
            body = DONE_RE.sub('', line).strip()
            check_skill(body)
            print(f'\n{BOLD}{c("92")}  ✓ Agent finished: {highlight_keywords(body)}{RESET}\n', flush=True)
            continue

        if THINK_RE.search(line):
            in_thinking = True
            in_output   = False
            body = THINK_RE.sub('', line).strip()
            check_skill(body)
            print(f'{c("38;5;111")}  ✦ {highlight_keywords(body)}{RESET}', flush=True)
            continue

        if EXEC_RE.match(line):
            in_thinking = False
            in_output   = False
            body = EXEC_RE.sub('', line)
            check_skill(body)
            print(f'\n{c("32")}{BOLD}  $ {RESET}{c("32")}{highlight_keywords(body)}{RESET}', flush=True)
            continue

        if OUTPUT_RE.match(line):
            in_thinking = False
            in_output   = True
            body = OUTPUT_RE.sub('', line)
            if body.strip():
                print(f'{DIM}{c("37")}  ⟶ {body}{RESET}', flush=True)
            continue

        if in_thinking and line.strip() and not SECTION_RE.match(line):
            check_skill(line)
            print(f'{c("38;5;111")}    {highlight_keywords(line)}{RESET}', flush=True)
            continue

        if in_output and line.strip() and not SECTION_RE.match(line):
            print(f'{DIM}{c("37")}    {line}{RESET}', flush=True)
            continue

        in_thinking = in_output = False
        if line.strip():
            print(f'{DIM}{line}{RESET}', flush=True)

except KeyboardInterrupt:
    pass
PYEOF

JOBS_DIR="$SCRIPT_DIR/jobs"
JOB_DIR="$JOBS_DIR/$JOB_NAME"

# ── Dry-run: inject a synthetic mission plan and jump straight to viz ─────────
if $DRY_RUN; then
    echo "[DRY RUN] Generating synthetic mission plan..."
    DRY_DIR="$JOBS_DIR/dry-run/task__dryrun/artifacts"
    mkdir -p "$DRY_DIR"
    python3 - "$DRY_DIR/mission_plan.json" <<'PYEOF'
import json, sys, math, random

random.seed(42)

# Fake Venus gravity-assist + deep-space mission
phases = [
    {
        "phase": "earth_departure",
        "date": "2028-03-15",
        "maneuver": "departure_burn",
        "delta_v_km_s": 3.621,
        "from_body": "EARTH",
        "to_body": "VENUS",
        "parking_orbit_radius_km": 6678.0,
        "transfer_orbit": {"a_km": 131_500_000, "e": 0.2107, "i_deg": 0.31},
    },
    {
        "phase": "flyby",
        "date": "2028-07-04",
        "maneuver": "venus_gravity_assist",
        "delta_v_km_s": 0.0,
        "body": "VENUS",
        "periapsis_km": 6351.0,
        "turn_angle_deg": 38.7,
        "from_body": "VENUS",
        "to_body": "DEEP_SPACE",
        "post_flyby_orbit": {"a_km": 480_000_000, "e": 0.712, "i_deg": 3.4},
    },
    {
        "phase": "deep_space",
        "date": "2030-11-20",
        "maneuver": "apoapsis_coast",
        "delta_v_km_s": 0.0,
        "from_body": "DEEP_SPACE",
        "to_body": "DEEP_SPACE",
        "transfer_orbit": {"a_km": 480_000_000, "e": 0.712, "i_deg": 3.4},
    },
    {
        "phase": "earth_return",
        "date": "2031-06-30",
        "maneuver": "return_burn",
        "delta_v_km_s": 4.812,
        "from_body": "DEEP_SPACE",
        "to_body": "EARTH",
        "transfer_orbit": {"a_km": 270_000_000, "e": 0.445, "i_deg": 1.2},
    },
    {
        "phase": "earth_arrival",
        "date": "2033-01-15",
        "maneuver": "capture_burn",
        "delta_v_km_s": 3.556,
        "from_body": "EARTH",
        "to_body": "EARTH",
        "capture_orbit": {"periapsis_km": 6678.0, "period_hours": 1.5},
    },
]

total_dv = sum(p["delta_v_km_s"] for p in phases)

plan = {
    "mission_name": "Deep Space Mission",
    "strategy": "gravity_assist",
    "departure_date": "2028-03-15",
    "return_date": "2033-01-15",
    "total_delta_v_km_s": round(total_dv, 4),
    "max_distance_AU": 5.23,
    "phases": phases,
    "verification": {
        "total_delta_v_check": True,
        "mission_duration_days": 1767,
        "earth_return_distance_km": 0.0,
        "all_constraints_satisfied": True,
    },
}

with open(sys.argv[1], "w") as f:
    json.dump(plan, f, indent=2)

print(f"  Wrote synthetic plan: {sys.argv[1]}")
PYEOF

    JOB_DIR="$JOBS_DIR/dry-run"
    TRIAL_DIR="$JOB_DIR/task__dryrun"
    TRIAL_NAME="task__dryrun"
    ARTIFACT_PATH="$DRY_DIR/mission_plan.json"
    REWARD="dry-run"
    mkdir -p "$TRIAL_DIR/verifier"
    echo "dry-run" > "$TRIAL_DIR/verifier/reward.txt"

    echo ""
    echo "  Skipping steps 1–2 (no agent, no Harbor)."
    echo "  Jumping straight to conversion + visualizer..."
    echo ""

    # Skip straight to step 4
    goto_step4=true
fi

# ── Step 1: Capture mission objective ────────────────────────────────────────
if $SKIP_AGENT; then
    echo "[1/5] Skipping prompt capture (--skip-agent), finding latest job..."
    JOB_DIR=$(ls -dt "$JOBS_DIR"/*/ 2>/dev/null | head -1)
    if [[ -z "$JOB_DIR" ]]; then
        echo "ERROR: No existing jobs found in $JOBS_DIR"
        exit 1
    fi
    JOB_DIR="${JOB_DIR%/}"
    JOB_NAME=$(basename "$JOB_DIR")
    echo "  Using job: $JOB_NAME"
else
    echo "[1/5] Opening visualizer for mission objective input..."

    # Ensure visualizer deps are installed
    cd "$VISUALIZER_DIR"
    if [[ ! -d "node_modules" ]]; then
        echo "  Installing visualizer dependencies..."
        npm install --silent
    fi

    # Create empty log file so the capture server can start tailing immediately
    touch "$LOG_FILE"

    # Start the capture + SSE server
    python3 "$SCRIPT_DIR/capture_server.py" "$PROMPT_FILE" "$LOG_FILE" "$CAPTURE_PORT" &
    CAPTURE_PID=$!
    sleep 1  # give the server a moment to bind

    # Start Vite dev server
    npm run dev -- --port "$VITE_PORT" --strictPort &
    VITE_PID=$!
    sleep 3  # give Vite time to compile

    # Open browser to prompt mode
    PROMPT_URL="http://localhost:$VITE_PORT/?mode=prompt"
    echo "  Opening $PROMPT_URL"
    open "$PROMPT_URL" 2>/dev/null \
        || xdg-open "$PROMPT_URL" 2>/dev/null \
        || echo "  (could not auto-open — navigate there manually)"

    # Poll for the objective file (set when user clicks "Run Mission")
    echo ""
    echo "  Waiting for mission objective to be submitted in the browser..."
    until [[ -f "$PROMPT_FILE" ]]; do sleep 0.5; done

    MISSION_OBJECTIVE=$(python3 -c "
import json, sys
print(json.load(open(sys.argv[1]))['objective'])
" "$PROMPT_FILE")

    echo ""
    echo "  Objective captured:"
    echo "  → $MISSION_OBJECTIVE"
    echo ""

    # Kill the Vite dev server (capture server stays alive for SSE)
    kill "$VITE_PID" 2>/dev/null || true
    wait "$VITE_PID" 2>/dev/null || true
    VITE_PID=""

    # Build a temp task directory with the objective injected into instruction.md
    TASK_TMP_DIR="$(mktemp -d)/task"
    cp -r "$SCRIPT_DIR/task/." "$TASK_TMP_DIR/"

    python3 - "$MISSION_OBJECTIVE" "$TASK_TMP_DIR/instruction.md" <<'PYEOF'
import sys, re

objective = sys.argv[1]
path      = sys.argv[2]
text      = open(path).read()

# Replace {{MISSION_OBJECTIVE}} placeholder if present
if "{{MISSION_OBJECTIVE}}" in text:
    text = text.replace("{{MISSION_OBJECTIVE}}", objective)
else:
    # Fallback: replace the hardcoded goal sentence
    text = re.sub(
        r"(Your goal is to ).*?(?=\n)",
        r"\g<1>" + objective,
        text,
        count=1,
    )

open(path, "w").write(text)
PYEOF
fi

# ── Step 2: Run agent via Harbor ──────────────────────────────────────────────
if ! $SKIP_AGENT; then
    echo "[2/5] Running ClaudeAgent via Harbor..."
    echo "  Job: $JOB_NAME  |  Model: $MODEL"
    echo ""

    TASK_DIR="${TASK_TMP_DIR:-$SCRIPT_DIR/task}"

    # Clear stale mission data so the visualizer shows a blank state while the agent runs
    echo '{"mission_name":"","status":"computing"}' > "$VISUALIZER_DIR/src/data/generatedMission.json"

    # Run Harbor in background so we can poll for the trial dir simultaneously
    # stdout → tee (raw to LOG_FILE) → skill_highlight (colored to terminal)
    PYTHONPATH="$SCRIPT_DIR" uvx --python 3.12 --with anthropic harbor run \
        -p "$TASK_DIR" \
        --agent-import-path agent.claude_agent:ClaudeAgent \
        -m "$MODEL" \
        --job-name "$JOB_NAME" \
        --artifact /app/mission_plan.json \
        $DEBUG_FLAG \
        2>&1 | tee -a "$LOG_FILE" | python3 "$HIGHLIGHT_PY" &
    HARBOR_PID=$!

    # Poll for the trial directory and conversation JSONL, then send path to SSE server
    (
        until TRIAL=$(ls -d "$JOB_DIR"/task__*/ 2>/dev/null | head -1); [ -n "$TRIAL" ]; do
            sleep 1
        done
        JSONL="$TRIAL/agent/conversation_turns.jsonl"
        until [ -f "$JSONL" ]; do sleep 1; done
        curl -s -X POST "http://localhost:$CAPTURE_PORT/set-jsonl" \
             -H "Content-Type: application/json" \
             -d "{\"path\": \"$JSONL\"}" || true
        echo "  [jsonl] Streaming from: $JSONL"
    ) &
    JSONL_WATCHER_PID=$!

    # Wait for Harbor to finish
    wait $HARBOR_PID || true
    AGENT_EXIT=$?
    
    # Wait for JSONL watcher to finish (it should exit once Harbor does)
    wait $JSONL_WATCHER_PID 2>/dev/null || true

    echo ""
    echo "  Agent run complete (exit: $AGENT_EXIT)."

    # Signal the SSE server that the agent is done
    echo "  Signaling capture server to stop..."
    curl -s -X POST "http://localhost:$CAPTURE_PORT/done" \
         -H "Content-Type: application/json" \
         -d "{\"exit_code\": $AGENT_EXIT}" || true

    # Wait for capture server to shut itself down (max 5s)
    (sleep 5; kill "$CAPTURE_PID" 2>/dev/null || true) &
    SHUTDOWN_WATCH_PID=$!
    wait "$CAPTURE_PID" 2>/dev/null || true
    kill "$SHUTDOWN_WATCH_PID" 2>/dev/null || true
    CAPTURE_PID=""
else
    echo "[2/5] Skipping agent run (--skip-agent)."
fi

# ── Step 3: Extract mission plan from artifacts ───────────────────────────────
if $DRY_RUN; then
    echo "[3/5] Skipping artifact extraction (dry-run — plan already created)."
    echo "  Artifact: $ARTIFACT_PATH"
else
    echo "[3/5] Extracting mission plan from job artifacts..."

    TRIAL_DIR=$(ls -d "$JOB_DIR"/task__*/ 2>/dev/null | head -1)
    if [[ -z "$TRIAL_DIR" ]]; then
        echo "ERROR: No trial directory found in $JOB_DIR"
        exit 1
    fi
    TRIAL_DIR="${TRIAL_DIR%/}"
    TRIAL_NAME=$(basename "$TRIAL_DIR")

    ARTIFACT_PATH="$TRIAL_DIR/artifacts/mission_plan.json"
    if [[ ! -f "$ARTIFACT_PATH" ]]; then
        ARTIFACT_PATH=$(find "$TRIAL_DIR/artifacts" -name "mission_plan.json" 2>/dev/null | head -1)
    fi

    if [[ -z "$ARTIFACT_PATH" || ! -f "$ARTIFACT_PATH" ]]; then
        echo "ERROR: mission_plan.json not found in artifacts."
        echo "  Looked in: $TRIAL_DIR/artifacts/"
        cat "$TRIAL_DIR/verifier/test-stdout.txt" 2>/dev/null || echo "  (no verifier output)"
        exit 1
    fi

    echo "  Found: $ARTIFACT_PATH"
    REWARD=$(cat "$TRIAL_DIR/verifier/reward.txt" 2>/dev/null || echo "unknown")
    echo "  Reward: $REWARD"
fi

# ── Step 4: Convert to visualizer format ─────────────────────────────────────
echo "[4/5] Converting mission plan to visualizer format..."

VISUALIZER_JSON="$VISUALIZER_DIR/src/data/generatedMission.json"

uv run --with pyyaml python3 -c "
import json, sys, math

with open('$ARTIFACT_PATH') as f:
    plan = json.load(f)

AU_KM  = 149_597_870.7
mu_sun = 1.327124400189e11

mission_name   = plan.get('mission_name', 'Agent Mission')
departure_date = plan.get('departure_date', '')
total_dv       = plan.get('total_delta_v_km_s', 0)
max_dist       = plan.get('max_distance_AU', 0)
dep_date       = plan.get('departure_date', '')
ret_date       = plan.get('return_date', '')
duration       = plan.get('verification', {}).get('mission_duration_days', 0)
if not duration and dep_date and ret_date:
    from datetime import datetime
    duration = (datetime.strptime(ret_date, '%Y-%m-%d') - datetime.strptime(dep_date, '%Y-%m-%d')).days

tier = 'Platinum' if max_dist >= 6 else 'Gold' if max_dist >= 4 else 'Silver' if max_dist >= 2 else 'Bronze'

dv_breakdown = {p.get('phase','?'): p.get('delta_v_km_s',0) for p in plan.get('phases', [])}

viz_phases = []
for phase in plan.get('phases', []):
    orbit = None
    transfer = phase.get('transfer_orbit') or phase.get('post_flyby_orbit')
    if transfer:
        a_km = transfer.get('a_km', 0)
        e    = transfer.get('e', 0)
        if a_km > 0:
            orbit = {
                'a_AU':        round(a_km / AU_KM, 4),
                'e':           round(e, 6),
                'omega_rad':   transfer.get('omega_rad', 0),
                'period_days': round(2 * math.pi * math.sqrt(a_km**3 / mu_sun) / 86400),
            }
    viz_phases.append({
        'phase':        phase.get('phase', ''),
        'date':         phase.get('date', ''),
        'delta_v_km_s': phase.get('delta_v_km_s', 0),
        'orbit':        orbit,
        'description':  phase.get('maneuver', phase.get('phase', '')),
    })

flybys = [
    {
        'planet':              p.get('body', ''),
        'date':                p.get('date', ''),
        'periapsis_altitude_km': p.get('periapsis_km', 0),
        'turn_angle_deg':      p.get('turn_angle_deg', 0),
        'incoming_v_inf_km_s': 0,
        'outgoing_v_inf_km_s': 0,
    }
    for p in plan.get('phases', []) if p.get('phase') == 'flyby'
]

viz = {
    'mission_name':         mission_name,
    'departure_date':       departure_date,
    'total_delta_v_km_s':   total_dv,
    'max_distance_AU':      max_dist,
    'mission_duration_days': duration,
    'tier':                 tier,
    'verification': {'mission_duration_days': duration, 'delta_v_breakdown_km_s': dv_breakdown},
    'phases':               viz_phases,
    'flybys':               flybys,
}
with open('$VISUALIZER_JSON', 'w') as f:
    json.dump(viz, f, indent=2)

print(f'  {mission_name}  |  {tier}  |  {max_dist:.3f} AU  |  Δv {total_dv:.3f} km/s  |  {duration} days')
"

echo "  Written: src/data/generatedMission.json"

# ── Step 5: Build and launch visualizer ──────────────────────────────────────
echo "[5/5] Launching mission visualizer..."

# Kill any stale capture server so the visualizer never shows the computing overlay
lsof -ti:$CAPTURE_PORT 2>/dev/null | xargs kill -9 2>/dev/null || true

cd "$VISUALIZER_DIR"

echo "  Building..."
npm run build --silent

pkill -f "vite preview" 2>/dev/null || true
sleep 1

echo ""
echo "=== Mission Visualizer Ready ==="
echo "  Job: $JOB_NAME  (trial: $TRIAL_NAME)"
echo "  Reward: $REWARD"
echo ""
echo "  http://localhost:4173/?mission=generated&autoplay=1"
echo ""

npx vite preview --port 4173 &
PREVIEW_PID=$!
sleep 2

open "http://localhost:4173/?mission=generated&autoplay=1" 2>/dev/null \
    || xdg-open "http://localhost:4173/?mission=generated&autoplay=1" 2>/dev/null \
    || echo "  Navigate to: http://localhost:4173/?mission=generated&autoplay=1"

echo ""
echo "  Press Ctrl+C to stop."
wait $PREVIEW_PID
