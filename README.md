# Skillathon — The First Agent Skills Hackathon

> AI agents are powerful, but they still fail at real work. Agent Skills inject transferable procedural knowledge to let them tackle hard problems.

## Event Details

- **Date:** March 7, 2026
- **Location:** Founders, Inc. — San Francisco, CA (Building C, Floor 3)
- **Format:** Solo or Teams of 2–5
- **Duration:** One-day event

**Links:**
- [Event Page (Luma)](https://luma.com/1khurilu?tk=hxWi5q)
- [Skillathon Website](https://www.skillathon.ai/)

## Background

Built on the momentum of [SkillsBench](https://arxiv.org/abs/your-link) (the largest benchmark for agent skills) and [Sundial](https://sundial.so) (the largest registry and toolbox for building skills), Skillathon brings builders together to craft quality skills and tasks to evaluate them.

## spacecraft_sim Package

The `task/environment/setup/spacecraft_sim/` directory contains an extracted orbital mechanics engine from [SpacecraftSimulator](https://github.com/) (Alessio Negri, LGPL v3). It provides headless, GUI-free computation for the Deep Space Explorer task.

Modules:
- `astronomical_data` — Planetary data, gravitational parameters, JPL orbital elements & rates
- `interplanetary_trajectories` — Ephemeris (Alg 8.1), Lambert transfers (Alg 8.2), departures, arrivals, flybys, pork chop data
- `orbit_determination` — Lambert solver (Alg 5.2), Julian day, coordinate transforms
- `orbital_maneuvers` — Hohmann, bi-elliptic, propellant mass (Tsiolkovsky)
- `lagrange_coefficients` — Orbit propagation via universal variable (Alg 3.3, 3.4)
- `three_dimensional_orbit` — Orbital elements ↔ state vectors (Alg 4.2, 4.5)
- `two_body_problem` — Orbital parameters, relative motion integration
- `time_utils` — Time ↔ anomaly conversions (circular, elliptical, parabolic, hyperbolic)

Dependencies: `numpy>=1.24`, `scipy>=1.10`. Python ≥3.9 (no match/case — uses dict lookups).

Reference: "Orbital Mechanics for Engineering Students" — Howard D. Curtis.

## Project Structure (Harbor Format)

Submissions use the [Harbor task format](https://harborframework.com/docs/tasks):

```
task/
├── instruction.md          # Task prompt the agent receives
├── task.toml               # Configuration & metadata
├── environment/
│   ├── Dockerfile          # Container environment definition
│   └── setup/
│       └── spacecraft_sim/ # Orbital mechanics Python package (installed in container)
├── solution/
│   ├── solve.sh            # Oracle entry point
│   └── solve.py            # Oracle Lambert solver implementation
└── tests/
    ├── test.sh             # Verification entry point
    └── verify_mission.py   # Constraint checker & reward calculator
```

### Quick Reference

- `instruction.md` — The markdown instruction given to the agent.
- `task.toml` — Metadata (author, difficulty, tags) and config (timeouts, resources).
- `environment/Dockerfile` — Defines the container the agent works in. Based on Ubuntu 22.04 with Python 3, pip, and `spacecraft_sim` pre-installed.
- `solution/solve.sh` / `solve.py` — Programmatic oracle solution (Lambert Earth-Mars round trip). Used to validate the task is solvable.
- `tests/test.sh` / `verify_mission.py` — Runs after the agent finishes; validates 6 constraints and writes a reward (0.0–2.0) to `/logs/verifier/reward.txt`.

---

## Running Locally — Complete Guide

There are **four ways** to run this project, from simplest to most complete:

| Method | Docker? | Harbor? | API Key? | What it does |
|--------|---------|---------|----------|--------------|
| [Standalone solver](#1-standalone-solver-run-mission-e2esh) | No | No | No | Runs a Python Lambert solver, verifies, visualizes |
| [Docker E2E pipeline](#2-docker-e2e-pipeline-no-harbor) | Yes | No | No | Runs oracle + verifier inside Docker |
| [Interactive simulation](#3-interactive-agent-simulation) | Yes | No | No | Drop into the container to manually solve |
| [Full agent run](#4-full-agent-run-via-harbor) | Yes | Yes | Yes | Runs ClaudeAgent autonomously via Harbor |

### Prerequisites

| Requirement | Needed for |
|-------------|------------|
| Python 3.9+ | All methods |
| Node.js + npm | Visualizer (methods 1, agent+visualize) |
| Docker (running) | Methods 2, 3, 4 |
| `harbor-bench` pip package | Method 4 only |
| `anthropic` pip package | Method 4 only |
| `ANTHROPIC_API_KEY` | Method 4 only |

### Setup

```bash
# Create and activate a virtualenv
python3 -m venv ~/.virtualenvs/skillathon
source ~/.virtualenvs/skillathon/bin/activate
# — or with virtualenvwrapper —
mkvirtualenv skillathon

# Install dependencies
pip install -r requirements.txt

# Store your Anthropic API key (needed only for agent runs)
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env.local
```

---

### 1. Standalone Solver (`run-mission-e2e.sh`)

The fastest way to generate and visualize a mission. No Docker, no Harbor, no API key.

**What it does:**
1. Sets up a local Python venv in `task/environment/setup/` and installs `spacecraft_sim`
2. Runs an inline Lambert solver (Earth→Mars→Earth) or uses a hardcoded sample
3. Verifies the mission plan (delta-v budget, duration, tier)
4. Copies the JSON to `mission-visualizer/src/data/generatedMission.json`
5. Starts the Vite dev server to display the result

```bash
# Generate a mission with the Lambert solver and visualize
./run-mission-e2e.sh

# Use a hardcoded sample mission instead of solving
./run-mission-e2e.sh --sample

# Auto-open browser after starting
./run-mission-e2e.sh --open
```

**Where outputs go:**
| Output | Location |
|--------|----------|
| Mission plan JSON | `/tmp/mission_plan.json` (intermediate) |
| Visualizer copy | `mission-visualizer/src/data/generatedMission.json` |
| Visualizer URL | `http://localhost:5173/?mission=generated` |

**Console output** shows the solver results (delta-v, distance, duration, tier) and verification status.

---

### 2. Docker E2E Pipeline (no Harbor)

Verifies the full oracle → verifier → reward pipeline inside Docker, without needing Harbor.

```bash
# 1. Build the environment image (context must be task/environment/)
docker build -t spacecraft-test -f task/environment/Dockerfile task/environment/

# 2. Run oracle + verifier end-to-end
docker run --rm \
  -v "$(pwd)/task/solution:/solution" \
  -v "$(pwd)/task/tests:/tests" \
  spacecraft-test bash -c '
    mkdir -p /app /logs/verifier
    bash /solution/solve.sh
    bash /tests/test.sh
    cat /logs/verifier/reward.txt
  '
```

**What happens inside the container:**
1. `solve.sh` → calls `solve.py` → writes `/app/mission_plan.json`
2. `test.sh` → calls `verify_mission.py` → reads the plan, checks 6 constraints, computes reward
3. Reward (0.0–2.0) is written to `/logs/verifier/reward.txt`

**Where outputs go:**
| Output | Location (inside container) |
|--------|----------------------------|
| Mission plan | `/app/mission_plan.json` |
| Reward score | `/logs/verifier/reward.txt` |
| Verifier details | stdout (JSON with errors, warnings, tier) |

> **Note:** The oracle currently exceeds the 12 km/s delta-v budget (the optimization problem is intentionally hard), so it scores 0 — but the pipeline runs cleanly.

---

### 3. Interactive Agent Simulation

Drop into the Docker container to manually solve the task, exactly as the agent would experience it.

```bash
# 1. Build the image
docker build -t spacecraft-test -f task/environment/Dockerfile task/environment/

# 2. Start an interactive container
docker run --rm -it \
  -v "$(pwd)/task/instruction.md:/app/instruction.md:ro" \
  -v "$(pwd)/task/tests:/tests:ro" \
  spacecraft-test bash
```

**Inside the container you have:**
| Resource | Path | Description |
|----------|------|-------------|
| Task prompt | `/app/instruction.md` | The instruction the agent reads |
| spacecraft_sim | Pre-installed | Orbital mechanics Python package |
| Verifier | `/tests/test.sh` | Run when done to score your solution |

```bash
# Example: query Mars position
python3 -c "
from spacecraft_sim import InterplanetaryTrajectories, CelestialBody
from datetime import datetime
r, v = InterplanetaryTrajectories.ephemeris(CelestialBody.MARS, datetime(2028, 9, 15))
print('Mars position:', r)
"

# After producing /app/mission_plan.json, run the verifier
mkdir -p /logs/verifier
bash /tests/test.sh
cat /logs/verifier/reward.txt
```

---

### 4. Full Agent Run via Harbor

Runs the `ClaudeAgent` autonomously inside a Docker container via the Harbor evaluation framework.

#### Running with the Oracle Agent

The oracle agent runs `task/solution/solve.sh` inside the container. Useful for verifying the environment builds and the verifier works:

```bash
source ~/.virtualenvs/skillathon/bin/activate  # or: workon skillathon
harbor run -p task/ -a oracle --job-name oracle-test --debug
```

#### Running with the Custom Claude Agent

```bash
source ~/.virtualenvs/skillathon/bin/activate

# Load API key and run
source .env.local 2>/dev/null
PYTHONPATH=. ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  harbor run -p task/ \
    --agent-import-path agent.claude_agent:ClaudeAgent \
    -m anthropic/claude-sonnet-4-20250514 \
    --job-name my-run \
    --artifact /app/mission_plan.json \
    --debug
```

**Harbor flags:**

| Flag | Purpose |
|------|---------|
| `--agent-import-path` | Python import path to the custom agent class |
| `-m` | Model name (prefix with provider, e.g. `anthropic/`) |
| `--job-name` | Name for the job directory under `jobs/` (default: timestamp) |
| `--artifact` | Path inside the container to extract after the run (repeatable) |
| `--debug` | Verbose logging |
| `--no-delete` | Keep the Docker container after the run (useful for debugging) |

---

## Output Directory Structure

All Harbor runs write results to `jobs/<job-name>/`. Here is the complete layout:

```
jobs/<job-name>/
├── result.json                        # Job-level summary (reward, timing, token usage)
├── config.json                        # Run configuration (model, flags, paths)
├── job.log                            # Harbor orchestration log
│
└── task__<trial-id>/                  # Trial directory (one per task)
    ├── result.json                    # Trial result (reward, agent info)
    ├── trial.log                      # Agent execution log (all commands run)
    ├── config.json                    # Trial-specific config
    │
    ├── agent/                         # Conversation logs (added in agent v0.3.0)
    │   ├── conversation.json          # Full conversation snapshot (overwritten each turn)
    │   └── conversation_turns.jsonl   # Append-only per-turn JSONL log
    │
    ├── artifacts/                     # Files extracted from the container
    │   └── mission_plan.json          # The agent's mission plan (if --artifact was used)
    │
    └── verifier/                      # Verification results
        ├── reward.txt                 # Numeric reward (0.0–2.0)
        └── test-stdout.txt            # Verifier output (tier, errors, warnings, JSON details)
```

### Key Output Files Explained

**`result.json` (job-level)** — Top-level summary including the final reward, total wall-clock time, and aggregate token usage across all trials.

**`trial.log`** — Full log of every bash command the agent executed inside the container, with stdout/stderr output. This is the primary debugging artifact.

**`agent/conversation.json`** — Complete conversation state: system prompt, model name, all messages (user + assistant + tool results), and cumulative token counts. Overwritten each turn. Useful for replaying or debugging the full agent session.

**`agent/conversation_turns.jsonl`** — Append-only log with one JSON object per turn. Each entry includes:
- The assistant's response blocks (reasoning text + tool calls)
- Tool execution results (full stdout/stderr/exit code)
- Per-turn token usage (input_tokens, output_tokens)

**`artifacts/mission_plan.json`** — The mission plan JSON produced by the agent at `/app/mission_plan.json` inside the container, extracted by Harbor's `--artifact` flag.

**`verifier/reward.txt`** — The numeric reward: `0.0` if any constraint is violated, otherwise `min(max_distance_AU / 6.0, 2.0)`.

**`verifier/test-stdout.txt`** — Full verifier output including:
- JSON details (max_distance_AU, total_delta_v_km_s, duration_days, errors, warnings)
- Constraint violation list (if any)
- Tier classification and final reward

### Quick Commands to Inspect Results

```bash
# Check reward and tier for a specific job
cat jobs/my-run/task__*/verifier/reward.txt
cat jobs/my-run/task__*/verifier/test-stdout.txt

# View the extracted mission plan
cat jobs/my-run/task__*/artifacts/mission_plan.json | python3 -m json.tool

# Check job-level summary (reward, timing, tokens)
cat jobs/my-run/result.json | python3 -m json.tool

# View agent conversation (what the agent said and did)
cat jobs/my-run/task__*/agent/conversation_turns.jsonl | head -5

# List all jobs sorted by date
ls -lt jobs/

# Find the highest-scoring run
for d in jobs/*/task__*/verifier/reward.txt; do echo "$(cat $d) $d"; done | sort -rn
```

---

## Verification & Scoring

The verifier (`task/tests/verify_mission.py`) checks 6 constraints. Violating any one results in a reward of 0.

| # | Constraint | Limit |
|---|-----------|-------|
| 1 | Total delta-v of all maneuvers | ≤ 12.0 km/s (with 5% tolerance) |
| 2 | Mission duration | ≤ 7305 days (20 years) |
| 3 | Return trajectory arrives within Earth's SOI | ~925,000 km |
| 4 | Flyby periapsis above planet surface | + 300 km minimum |
| 5 | Orbital elements physically valid | e ≥ 0, a > 0 for elliptical |
| 6 | Departs from 300 km circular LEO | r = 6678 km |

**Scoring tiers** (based on maximum heliocentric distance achieved):

| Tier | Distance | Reward Range | Description |
|------|----------|-------------|-------------|
| Bronze | 1.5–2.0 AU | 0.25–0.33 | Mars-class mission |
| Silver | 2.0–4.0 AU | 0.33–0.67 | Asteroid belt reach |
| Gold | 4.0–6.0 AU | 0.67–1.0 | Jupiter-class (requires gravity assist) |
| Platinum | > 6.0 AU | 1.0–2.0 | Saturn-class or beyond |

Reward formula: `min(max_distance_AU / 6.0, 2.0)` if all constraints pass, else `0.0`.

---

## E2E Scripts

Two scripts automate the full pipeline from mission generation to visualization.

### `run-mission-e2e.sh` — Standalone Solver + Visualizer

Runs an inline Python Lambert solver (no agent, no Docker, no Harbor) to generate a mission plan, then launches the visualizer. Useful for quick iteration on the visualizer itself or for demos.

Pipeline: Python Lambert solver → verify constraints → copy JSON → start Vite dev server

```bash
./run-mission-e2e.sh              # Generate and visualize
./run-mission-e2e.sh --sample     # Use hardcoded sample mission
./run-mission-e2e.sh --open       # Auto-open browser
```

| Requirement | Needed? |
|-------------|---------|
| Python 3.9+ | Yes |
| Node.js + npm | Yes |
| Docker | No |
| Harbor | No |
| API key | No |

Output served at `http://localhost:5173/?mission=generated`.

### `run-agent-visualize.sh` — Agent (Harbor) + Visualizer

Runs the `ClaudeAgent` via Harbor inside Docker, extracts the mission plan artifact, converts it to the visualizer format, and serves the result.

Pipeline: Harbor agent run (Docker) → extract `/app/mission_plan.json` → convert format → build visualizer → serve via `vite preview`

```bash
./run-agent-visualize.sh                          # Full pipeline
./run-agent-visualize.sh --job-name=my-run --open # Custom name + auto-open
./run-agent-visualize.sh --skip-agent             # Skip agent, visualize latest job
./run-agent-visualize.sh --model=anthropic/claude-sonnet-4-20250514
./run-agent-visualize.sh --debug                  # Harbor debug logging
```

| Option | Description |
|--------|-------------|
| `--job-name=NAME` | Custom Harbor job name (default: `agent-viz-<timestamp>`) |
| `--open` | Open browser after starting the visualizer |
| `--model=MODEL` | Model to use (default: `anthropic/claude-sonnet-4-20250514`) |
| `--skip-agent` | Skip agent run, use the latest existing job artifacts |
| `--debug` | Enable Harbor debug logging |

| Requirement | Needed? |
|-------------|---------|
| Python 3.9+ (in `skillathon` venv) | Yes |
| Node.js + npm | Yes |
| Docker (running) | Yes |
| `harbor-bench` + `anthropic` | Yes |
| `ANTHROPIC_API_KEY` in `.env.local` | Yes |

Output served at `http://localhost:4173/?mission=generated`.

---

## Mission Visualizer

The `mission-visualizer/` directory contains a React + TypeScript + D3.js web app that renders mission plans as interactive solar system diagrams.

### Architecture

Built with Vite, React 19, Tailwind CSS 4, Framer Motion, and D3.js.

```
mission-visualizer/src/
├── App.tsx                          # Main app — loads mission data, renders layout
├── components/
│   ├── SolarSystemView.tsx          # D3 SVG solar system with orbit rings and trajectory
│   ├── TrajectoryPath.tsx           # Animated trajectory arc rendering
│   ├── Timeline.tsx                 # Mission phase timeline
│   ├── DeltaVBudget.tsx             # Delta-v budget bar chart
│   ├── FlybyDetail.tsx              # Flyby info cards
│   └── Scoreboard.tsx              # Tier/reward display
├── data/
│   ├── sampleMission.json           # Built-in sample (always available)
│   ├── sampleMissionFlyby.json      # Sample with gravity assist
│   ├── generatedMission.json        # Written by E2E scripts (gitignored)
│   └── planets.ts                   # Planet orbital data for rendering
├── hooks/
│   └── useMissionData.ts            # Mission data loading hook
└── lib/
    ├── missionParser.ts             # JSON → internal model conversion
    ├── orbitalMath.ts               # Orbital mechanics for rendering
    └── scales.ts                    # D3 scale utilities
```

### Running the Visualizer Standalone

```bash
cd mission-visualizer
npm install
npm run dev          # Dev server at http://localhost:5173
npm run build        # Production build to dist/
npm run preview      # Serve production build at http://localhost:4173
npm run test         # Run tests (vitest)
```

### Mission Data Sources

The visualizer loads mission data based on the `?mission=` URL parameter:

| URL | Source |
|-----|--------|
| `http://localhost:5173/` | Default sample mission |
| `http://localhost:5173/?mission=sample` | `src/data/sampleMission.json` |
| `http://localhost:5173/?mission=generated` | `src/data/generatedMission.json` |

The `generatedMission.json` file is written by the E2E scripts and is gitignored.

---

## Custom LLM Agent (Claude)

The `agent/` directory contains a custom Harbor-compatible external agent powered by Anthropic Claude. It implements Harbor's `BaseAgent` interface and uses Claude's tool-use capability to autonomously solve tasks inside the container environment.

### Architecture

The agent follows a simple agentic loop:

1. Claude receives the task instruction as the initial user message
2. Claude reasons about the task and requests bash commands via tool use
3. The agent executes each command in the container via `environment.exec()`
4. Command output (stdout, stderr, exit code) is fed back to Claude
5. Repeat until Claude stops requesting tools or hits the turn limit

```
agent/
├── __init__.py
├── claude_agent.py        # BaseAgent implementation (agentic loop + logging)
└── skills/
    └── deep-space-explorer/
        └── SKILL.md       # Injected into system prompt at runtime
```

### Agent Skills

The agent automatically loads all `SKILL.md` files from `agent/skills/` and injects their content into the system prompt. This is how procedural knowledge (the "skill") is provided to the agent.

To add or modify skills, edit files under `agent/skills/<skill-name>/SKILL.md`. The YAML frontmatter is stripped; only the markdown body is injected.

### Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| Max turns | 15 | Maximum agentic loop iterations |
| Command timeout | 180s | Per-command execution timeout |
| Max output | 15,000 chars | Long outputs are truncated (first 7k + last 7k) |
| Default model | `claude-sonnet-4-20250514` | Overridable via `-m` flag |
| Agent version | 0.4.0 | Reported in Harbor metadata |

### Environment

The agent requires `ANTHROPIC_API_KEY` to be set. Store it in `.env.local`:

```bash
# .env.local
ANTHROPIC_API_KEY=sk-ant-...
```

### Running

```bash
source ~/.virtualenvs/skillathon/bin/activate

PYTHONPATH=. ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY .env.local | cut -d= -f2) \
  harbor run -p task/ \
    --agent-import-path agent.claude_agent:ClaudeAgent \
    -m anthropic/claude-sonnet-4-20250514 \
    --artifact /app/mission_plan.json \
    --job-name skill-run
```

### Dependencies

- `harbor` (v0.1.45+) — evaluation framework
- `anthropic` (v0.84+) — Claude API client
- Docker — container runtime for task environments

---

## Creating Agent Skills

[Agent Skills](https://blog.serghei.pl/posts/agent-skills-101/) are portable, version-controlled folders of procedural knowledge that teach AI agents how to perform specific tasks. They follow an [open standard](https://agentskills.io/) supported by 20+ platforms (Claude Code, Copilot, Cursor, Gemini CLI, Codex, etc.).

A skill is a directory containing a `SKILL.md` file with YAML frontmatter (metadata) and a markdown body (instructions).

### Skill Directory Structure

```
.agents/skills/my-skill/       # Cross-platform location
  SKILL.md                      # Required: metadata + instructions
  scripts/                      # Optional: loaded on demand
  references/                   # Optional: loaded on demand
  assets/                       # Optional: templates, examples
```

Platform-specific alternatives: `.claude/skills/`, `.cursor/skills/`, `.github/skills/`, `.kiro/skills/`.

### Minimal SKILL.md

```yaml
---
name: orbital-mission-planner
description: >
  Use when designing interplanetary trajectories, computing Lambert transfers,
  or optimizing delta-v budgets using the spacecraft_sim package.
  Handles ephemeris lookups, gravity assists, and mission constraint validation.
---

# Orbital Mission Planner

## Workflow

1. Read mission constraints from the task prompt (delta-v budget, duration limit, departure window)
2. Use `InterplanetaryTrajectories.ephemeris()` to get planetary positions at candidate dates
3. Solve Lambert problems with `OrbitDetermination.solve_lambert_problem()` for transfer orbits
4. Compute departure delta-v: `sqrt(v_inf^2 + 2*mu/r_p) - sqrt(mu/r_p)`
5. Check total delta-v against budget before committing to a trajectory
6. Write the mission plan JSON to `/app/mission_plan.json`

## Rules

- Always set `OrbitDetermination.set_celestial_body(CelestialBody.SUN)` before solving heliocentric Lambert problems
- Cast numpy types to Python native types before `json.dump` (numpy bools/floats are not JSON-serializable)
- Use `InterplanetaryTrajectories.flyby()` directly for gravity assists — the gravity assist path in `optimal_transfer()` is incomplete
- Apoapsis of a transfer orbit = `a * (1 + e)` from the Lambert solution orbital elements
```

### Key Principles

- The `description` field is a trigger, not a summary — it tells the agent *when* to activate, not *how* the workflow works. Keep it under 1,024 characters.
- The body is a procedure, not documentation — write actionable steps, not explanations.
- Skills use progressive disclosure: metadata loads at startup (~100 tokens), the body loads on activation, referenced files load on demand.
- Keep the body under 500 lines. Move reference material to `references/` files.

### Installing Community Skills

```bash
# From the skills.sh registry
npx skills add <owner>/<skill-name>

# Browse available skills at https://skills.sh
```

### Further Reading

- [Agent Skills 101](https://blog.serghei.pl/posts/agent-skills-101/) — practical guide to the format
- [Agent Skills Specification](https://agentskills.io/) — the open standard
- [Skills Directory](https://www.skillsdirectory.org/) — community skill catalog
- [Sundial](https://sundial.so) — registry and toolbox for building skills
