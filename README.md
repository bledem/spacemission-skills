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
│   └── Dockerfile          # Container environment definition
├── solution/
│   └── solve.sh            # Oracle solution for sanity-checking
└── tests/
    └── test.sh             # Verification script (produces reward file)
```

### Quick Reference

- `instruction.md` — The markdown instruction given to the agent.
- `task.toml` — Metadata (author, difficulty, tags) and config (timeouts, resources).
- `environment/Dockerfile` — Defines the container the agent works in.
- `solution/solve.sh` — Programmatic solution used by the Oracle agent to validate the task is solvable.
- `tests/test.sh` — Runs after the agent finishes; must write `1` (pass) or `0` (fail) to `/logs/verifier/reward.txt`.

### Running Locally

```bash
# Install Harbor
pip install harbor-bench

# Run your task with an agent
harbor run -p "task/" -a "<agent>" -m "<model>"
```

### Running the E2E Pipeline (Docker)

You can verify the full oracle → verifier → reward pipeline without Harbor:

```bash
# 1. Build the environment image
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

This mirrors what Harbor does at runtime:
1. `solve.sh` runs the oracle, which writes `/app/mission_plan.json`
2. `test.sh` calls `verify_mission.py`, which validates constraints and computes a score
3. The reward (0.0–2.0) is written to `/logs/verifier/reward.txt`

The oracle currently exceeds the 12 km/s delta-v budget (the optimization problem is intentionally hard), so it scores 0 — but the pipeline itself runs cleanly end-to-end.

### Simulating the Agent E2E

To simulate what an actual agent experiences (reading the prompt, writing code, producing a plan, getting scored):

```bash
# 1. Build the image
docker build -t spacecraft-test -f task/environment/Dockerfile task/environment/

# 2. Start an interactive container with the instruction + verifier mounted
docker run --rm -it \
  -v "$(pwd)/task/instruction.md:/app/instruction.md:ro" \
  -v "$(pwd)/task/tests:/tests:ro" \
  spacecraft-test bash

# Inside the container you now have:
#   /app/instruction.md   — the task prompt (what the agent reads)
#   spacecraft_sim         — pre-installed Python package
#   /tests/test.sh         — verifier (run when done)

# 3. Write your solution (agent or manual) — must produce /app/mission_plan.json
python3 -c "
from spacecraft_sim import InterplanetaryTrajectories, CelestialBody
from datetime import datetime
r, v = InterplanetaryTrajectories.ephemeris(CelestialBody.MARS, datetime(2028, 9, 15))
print('Mars position:', r)
"

# 4. After producing /app/mission_plan.json, run the verifier
mkdir -p /logs/verifier
bash /tests/test.sh
cat /logs/verifier/reward.txt
```

The verifier checks 6 constraints (delta-v budget, duration, Earth return, flyby altitude, physical validity, parking orbit) and scores based on maximum heliocentric distance achieved.

| Tier | Distance | Reward |
|------|----------|--------|
| Bronze | 1.5–2.0 AU | 0.25–0.33 |
| Silver | 2.0–4.0 AU | 0.33–0.67 |
| Gold | 4.0–6.0 AU | 0.67–1.0 |
| Platinum | > 6.0 AU | 1.0–2.0 |

## Custom LLM Agent (Claude)

The `agent/` directory contains a custom Harbor-compatible external agent powered by Anthropic Claude. It implements Harbor's `BaseAgent` interface and uses Claude's tool-use capability to autonomously solve tasks inside the container environment.

### Architecture

The agent follows a simple agentic loop:

1. Claude receives the task instruction as the initial user message
2. Claude reasons about the task and requests bash commands via tool use
3. The agent executes each command in the container via `environment.exec()`
4. Command output (stdout, stderr, exit code) is fed back to Claude
5. Repeat until Claude stops requesting tools or hits the 30-turn limit

```
agent/
├── __init__.py
└── claude_agent.py    # BaseAgent implementation
```

### Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| Max turns | 30 | Maximum agentic loop iterations |
| Command timeout | 120s | Per-command execution timeout |
| Max output | 15,000 chars | Long outputs are truncated to stay within context |
| Default model | `claude-sonnet-4-20250514` | Overridable via `-m` flag |

### Environment

The agent requires `ANTHROPIC_API_KEY` to be set. Store it in `.env.local`:

```bash
# .env.local
ANTHROPIC_API_KEY=sk-ant-...
```

### Running

```bash
# Activate the virtualenv with harbor installed
workon skillathon

# Run the custom agent against the task
PYTHONPATH=. ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY .env.local | cut -d= -f2) \
  harbor run -p task/ \
    --agent-import-path agent.claude_agent:ClaudeAgent \
    -m anthropic/claude-sonnet-4-20250514
```

### Dependencies

- `harbor` (v0.1.45+) — evaluation framework
- `anthropic` (v0.84+) — Claude API client
- Docker — container runtime for task environments

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

