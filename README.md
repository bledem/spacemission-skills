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

