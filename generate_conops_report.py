#!/usr/bin/env python3
"""Generate a CONOPS markdown report from a mission_plan.json file.

Usage:
    python generate_conops_report.py [mission_plan.json] [-o output.md]

Follows the 8-phase CONOPS template structure:
  1. Mission Overview
  2. Mission Requirements & Constraints
  3. Spacecraft Configuration
  4. Mission Design & Trajectory
  5. Concept of Operations (8 phases)
  6. Mission Timeline
  7. Risk Assessment
  8. Verification & Compliance
"""

import json
import sys
from datetime import datetime
from pathlib import Path

AU_KM = 149_597_870.7


def load_plan(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def fmt_date(d: str) -> str:
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%B %d, %Y")
    except (ValueError, TypeError):
        return d or "TBD"


def fmt_float(v, decimals: int = 3) -> str:
    if v is None:
        return "N/A"
    return f"{float(v):.{decimals}f}"


def section_mission_overview(plan: dict) -> str:
    name = plan.get("mission_name", "Unnamed Mission")
    objective = plan.get("mission_objective", plan.get("strategy", "N/A"))
    strategy = plan.get("strategy", "N/A")
    dep = fmt_date(plan.get("departure_date"))
    ret = fmt_date(plan.get("return_date"))
    duration = plan.get("verification", {}).get("mission_duration_days", "N/A")
    max_dist = plan.get("max_distance_AU", 0)

    lines = [
        "# CONOPS Report",
        "",
        f"## **{name}**",
        "",
        "---",
        "",
        "## 1. Mission Overview",
        "",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| **Mission Name** | {name} |",
        f"| **Objective** | {objective} |",
        f"| **Strategy** | {strategy.replace('_', ' ').title()} |",
        f"| **Departure Date** | {dep} |",
        f"| **Return / End Date** | {ret} |",
        f"| **Mission Duration** | {duration} days |",
        f"| **Max Distance** | {fmt_float(max_dist, 4)} AU ({fmt_float(max_dist * AU_KM, 0)} km) |",
    ]

    criteria = plan.get("success_criteria", [])
    if criteria:
        lines += [
            "",
            "### Success Criteria",
            "",
        ]
        for c in criteria:
            lines.append(f"- {c}")

    return "\n".join(lines)


def section_requirements(plan: dict) -> str:
    sc = plan.get("spacecraft", {})
    total_dv = plan.get("total_delta_v_km_s", 0)
    duration = plan.get("verification", {}).get("mission_duration_days", "N/A")

    lines = [
        "",
        "---",
        "",
        "## 2. Mission Requirements & Constraints",
        "",
        "| Requirement | Value | Status |",
        "|-------------|-------|--------|",
        f"| Total delta-v budget | {fmt_float(total_dv)} km/s | {'PASS' if total_dv <= 12.0 else 'OVER BUDGET'} |",
        f"| Mission duration | {duration} days | {'PASS' if isinstance(duration, (int, float)) and duration <= 7305 else 'CHECK'} |",
        f"| Spacecraft mass | {fmt_float(sc.get('mass_kg', 'N/A'), 1)} kg | - |",
        f"| Specific impulse | {fmt_float(sc.get('isp_s', 'N/A'), 0)} s | - |",
        f"| Propellant mass | {fmt_float(sc.get('fuel_kg', 'N/A'), 1)} kg | - |",
    ]
    return "\n".join(lines)


def section_spacecraft(plan: dict) -> str:
    sc = plan.get("spacecraft", {})
    if not sc:
        return ""

    mass = sc.get("mass_kg", 14.0)
    isp = sc.get("isp_s", 40)
    fuel = sc.get("fuel_kg", 5.4)
    dry = mass - fuel

    lines = [
        "",
        "---",
        "",
        "## 3. Spacecraft Configuration",
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| Wet mass | {fmt_float(mass, 1)} kg |",
        f"| Dry mass | {fmt_float(dry, 1)} kg |",
        f"| Propellant mass | {fmt_float(fuel, 1)} kg |",
        f"| Specific impulse | {fmt_float(isp, 0)} s |",
        f"| Mass ratio | {fmt_float(mass / dry if dry > 0 else 0, 3)} |",
    ]
    return "\n".join(lines)


def section_trajectory(plan: dict) -> str:
    phases = plan.get("phases", [])
    total_dv = plan.get("total_delta_v_km_s", 0)

    lines = [
        "",
        "---",
        "",
        "## 4. Mission Design & Trajectory",
        "",
        f"**Total Delta-V:** {fmt_float(total_dv)} km/s ({fmt_float(total_dv * 1000, 1)} m/s)",
        "",
        "### Maneuver Summary",
        "",
        "| # | Phase | Date | Delta-V (km/s) | Description |",
        "|----|-------|------|---------------|-------------|",
    ]

    for i, p in enumerate(phases, 1):
        phase = p.get("phase", "unknown")
        date = p.get("date", "TBD")
        dv = p.get("delta_v_km_s", 0)
        desc = p.get("maneuver", p.get("description", phase))
        lines.append(f"| {i} | {phase} | {date} | {fmt_float(dv)} | {desc} |")

    # Transfer orbit details
    dep_phase = next((p for p in phases if p.get("phase") == "earth_departure"), None)
    if dep_phase and dep_phase.get("transfer_orbit"):
        t = dep_phase["transfer_orbit"]
        a_km = t.get("a_km", 0)
        e = t.get("e", 0)
        i_deg = t.get("i_deg", 0)
        r_apo_km = a_km * (1 + e) if a_km > 0 else 0
        r_peri_km = a_km * (1 - e) if a_km > 0 else 0
        lines += [
            "",
            "### Transfer Orbit",
            "",
            "| Parameter | Value |",
            "|-----------|-------|",
            f"| Semi-major axis | {fmt_float(a_km, 0)} km ({fmt_float(a_km / AU_KM, 4)} AU) |",
            f"| Eccentricity | {fmt_float(e, 6)} |",
            f"| Inclination | {fmt_float(i_deg, 1)}° |",
            f"| Apoapsis | {fmt_float(r_apo_km, 0)} km ({fmt_float(r_apo_km / AU_KM, 4)} AU) |",
            f"| Periapsis | {fmt_float(r_peri_km, 0)} km ({fmt_float(r_peri_km / AU_KM, 4)} AU) |",
        ]

    # Flyby details
    flybys = [p for p in phases if p.get("phase") == "flyby"]
    if flybys:
        lines += ["", "### Gravity Assists", ""]
        for fb in flybys:
            body = fb.get("body", "Unknown")
            peri = fb.get("periapsis_km", 0)
            post = fb.get("post_flyby_orbit", {})
            lines += [
                f"**{body} Flyby** — {fb.get('date', 'TBD')}",
                "",
                f"- Periapsis: {fmt_float(peri, 0)} km",
                f"- Side: {fb.get('side', 'N/A')}",
                f"- Post-flyby apoapsis: {fmt_float(post.get('r_apoapsis_AU', 0), 2)} AU",
                "",
            ]

    return "\n".join(lines)


def section_conops(plan: dict) -> str:
    conops = plan.get("conops", {})
    if not conops:
        return ""

    lines = [
        "",
        "---",
        "",
        "## 5. Concept of Operations",
        "",
    ]

    # Phase 1: Launch
    launch = conops.get("launch", {})
    if launch:
        lines += [
            "### Phase 1: Launch & Deployment",
            "",
            "| Parameter | Value |",
            "|-----------|-------|",
            f"| Launch site | {launch.get('site', 'TBD')} |",
            f"| Launch vehicle | {launch.get('vehicle', 'TBD')} |",
            f"| Injection orbit | {launch.get('injection_orbit', 'TBD')} |",
            f"| Launch window | {launch.get('launch_window', 'TBD')} |",
        ]
        if launch.get("primary_mission"):
            lines.append(f"| Primary mission | {launch['primary_mission']} |")
        lines.append("")

    # Phase 2: Early Ops / LEOP
    early = conops.get("early_ops", {})
    if early:
        lines += [
            "### Phase 2: Early Orbit Operations (LEOP)",
            "",
            f"**Duration:** {early.get('duration_hours', 'TBD')} hours",
            "",
        ]
        activities = early.get("activities", [])
        if activities:
            lines.append("**Activities:**")
            for a in activities:
                lines.append(f"- {a}")
            lines.append("")
        constraints = early.get("constraints", [])
        if constraints:
            lines.append("**Constraints:**")
            for c in constraints:
                lines.append(f"- {c}")
            lines.append("")

    # Phase 3: Transfer
    transfer = conops.get("transfer", {})
    if transfer:
        lines += [
            "### Phase 3: Transfer Trajectory",
            "",
            "| Parameter | Value |",
            "|-----------|-------|",
            f"| Transfer type | {transfer.get('type', 'TBD')} |",
            f"| Duration | {transfer.get('duration_days', 'TBD')} days |",
            f"| Navigation | {transfer.get('nav_strategy', 'TBD')} |",
            "",
        ]
        tcm = transfer.get("tcm_schedule", [])
        if tcm:
            lines.append("**TCM Schedule:**")
            for t in tcm:
                lines.append(f"- {t}")
            lines.append("")

    # Phase 4: Cruise
    cruise = conops.get("cruise", {})
    if cruise:
        lines += [
            "### Phase 4: Cruise",
            "",
            "| Parameter | Value |",
            "|-----------|-------|",
            f"| Attitude mode | {cruise.get('mode', 'TBD')} |",
            f"| Pointing | {cruise.get('pointing', 'TBD')} |",
            f"| Power mode | {cruise.get('power_mode', 'TBD')} |",
            "",
        ]

    # Phase 5: Arrival
    arrival = conops.get("arrival", {})
    if arrival:
        lines += [
            "### Phase 5: Arrival & Orbit Insertion",
            "",
            "| Parameter | Value |",
            "|-----------|-------|",
            f"| Strategy | {arrival.get('strategy', 'TBD')} |",
        ]
        if arrival.get("loi_burn"):
            lines.append(f"| Insertion burn | {arrival['loi_burn']} |")
        if arrival.get("initial_orbit"):
            lines.append(f"| Initial orbit | {arrival['initial_orbit']} |")
        if arrival.get("orbit_determination"):
            lines.append(f"| Orbit determination | {arrival['orbit_determination']} |")
        if arrival.get("closest_approach_km"):
            lines.append(f"| Closest approach | {arrival['closest_approach_km']} km |")
        lines.append("")

    # Phase 6: Primary Ops
    ops = conops.get("primary_ops", {})
    if ops:
        lines += [
            "### Phase 6: Primary Science Operations",
            "",
            "| Parameter | Value |",
            "|-----------|-------|",
            f"| Operational orbit | {ops.get('orbit', 'TBD')} |",
            f"| Duration | {ops.get('duration_days', 'TBD')} days |",
            f"| Objective | {ops.get('objective', 'TBD')} |",
            f"| Observation strategy | {ops.get('observation_strategy', 'TBD')} |",
        ]
        if ops.get("coverage"):
            lines.append(f"| Coverage | {ops['coverage']} |")
        if ops.get("comms_windows"):
            lines.append(f"| Comm windows | {ops['comms_windows']} |")
        lines.append("")

        payloads = ops.get("payloads", [])
        if payloads:
            lines.append("**Payloads:**")
            for p in payloads:
                lines.append(f"- {p}")
            lines.append("")

        products = ops.get("data_products", [])
        if products:
            lines.append("**Data Products:**")
            for d in products:
                lines.append(f"- {d}")
            lines.append("")

    # Phase 7: Extended Ops
    ext = conops.get("extended_ops", {})
    if ext:
        lines += [
            "### Phase 7: Extended Mission",
            "",
            "| Parameter | Value |",
            "|-----------|-------|",
            f"| Entry condition | {ext.get('entry_condition', 'TBD')} |",
            f"| Duration | {ext.get('duration_days', 'TBD')} days |",
            f"| Objective | {ext.get('objective', 'TBD')} |",
            "",
        ]

    # Phase 8: End of Life
    eol = conops.get("end_of_life", {})
    if eol:
        lines += [
            "### Phase 8: End of Life & Disposal",
            "",
            "| Parameter | Value |",
            "|-----------|-------|",
            f"| Disposal strategy | {eol.get('disposal_strategy', 'TBD')} |",
        ]
        if eol.get("target"):
            lines.append(f"| Target | {eol['target']} |")
        if eol.get("disposal_delta_v_km_s") is not None:
            lines.append(f"| Disposal delta-v | {fmt_float(eol['disposal_delta_v_km_s'])} km/s |")
        if eol.get("final_spacecraft_state"):
            lines.append(f"| Final state | {eol['final_spacecraft_state']} |")
        lines.append("")

    return "\n".join(lines)


def section_timeline(plan: dict) -> str:
    timeline = plan.get("mission_timeline", [])
    if not timeline:
        return ""

    lines = [
        "",
        "---",
        "",
        "## 6. Mission Timeline",
        "",
        "| Date | Event |",
        "|------|-------|",
    ]
    for entry in timeline:
        lines.append(f"| {entry.get('date', 'TBD')} | {entry.get('event', '')} |")

    return "\n".join(lines)


def section_risks(plan: dict) -> str:
    risks = plan.get("risks", [])
    if not risks:
        return ""

    lines = [
        "",
        "---",
        "",
        "## 7. Risk Assessment",
        "",
        "| # | Risk | Probability | Impact | Mitigation |",
        "|----|------|-------------|--------|------------|",
    ]
    for i, r in enumerate(risks, 1):
        lines.append(
            f"| {i} "
            f"| {r.get('risk', '')} "
            f"| {r.get('probability', 'N/A')} "
            f"| {r.get('impact', 'N/A')} "
            f"| {r.get('mitigation', '')} |"
        )

    return "\n".join(lines)


def section_verification(plan: dict) -> str:
    v = plan.get("verification", {})
    if not v:
        return ""

    lines = [
        "",
        "---",
        "",
        "## 8. Verification & Compliance",
        "",
        "| Check | Value | Status |",
        "|-------|-------|--------|",
    ]

    dv_ok = v.get("total_delta_v_check", False)
    lines.append(f"| Delta-v within budget | {plan.get('total_delta_v_km_s', 'N/A')} km/s | {'PASS' if dv_ok else 'FAIL'} |")

    duration = v.get("mission_duration_days")
    if duration is not None:
        lines.append(f"| Mission duration | {duration} days | {'PASS' if duration <= 7305 else 'FAIL'} |")

    ret_dist = v.get("earth_return_distance_km")
    if ret_dist is not None:
        lines.append(f"| Earth return distance | {fmt_float(ret_dist, 0)} km | {'PASS' if ret_dist < 924631 else 'FAIL'} |")

    all_ok = v.get("all_constraints_satisfied", False)
    lines.append(f"| All constraints satisfied | — | {'PASS' if all_ok else 'FAIL'} |")

    # Any extra verification fields
    skip = {"total_delta_v_check", "mission_duration_days", "earth_return_distance_km", "all_constraints_satisfied"}
    for k, val in v.items():
        if k not in skip:
            lines.append(f"| {k.replace('_', ' ').title()} | {val} | — |")

    return "\n".join(lines)


def generate_report(plan: dict) -> str:
    sections = [
        section_mission_overview(plan),
        section_requirements(plan),
        section_spacecraft(plan),
        section_trajectory(plan),
        section_conops(plan),
        section_timeline(plan),
        section_risks(plan),
        section_verification(plan),
        "",
        "---",
        "",
        f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
    ]
    return "\n".join(sections) + "\n"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate CONOPS markdown from mission_plan.json")
    parser.add_argument("input", nargs="?", default="mission_plan.json", help="Input JSON file")
    parser.add_argument("-o", "--output", default=None, help="Output markdown file (default: stdout)")
    args = parser.parse_args()

    plan = load_plan(args.input)
    report = generate_report(plan)

    if args.output:
        Path(args.output).write_text(report)
        print(f"Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
