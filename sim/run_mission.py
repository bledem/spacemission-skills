"""CLI runner: execute a mission_plan.json through the sim engine.

Usage:
    python -m sim.run_mission mission_plan.json
    python -m sim.run_mission /tmp/mission_plan.json --verbose
"""

from __future__ import annotations

import json
import sys

from sim.bridge import convert_plan_to_conops
from sim.executor import execute_conops, MissionReport


def print_report(report: MissionReport, verbose: bool = False) -> None:
    print("=" * 60)
    print(f"Mission: {report.conops_name}")
    print(f"Score:   {report.score:.3f}")
    print(f"Status:  {report.final_status}")
    print(f"Delta-v: {report.total_delta_v_used_km_s:.4f} km/s")
    print(f"Fuel:    {report.total_fuel_consumed_kg:.3f} kg consumed")
    print(f"Duration: {report.total_duration_s / 86400:.1f} days")
    print("=" * 60)

    print(f"\n{'Phase':<15} {'OK':<4} {'Δv (km/s)':<12} {'Fuel (kg)':<10} {'Duration (d)':<12}")
    print("-" * 60)
    for p in report.phases:
        ok = "Y" if p.success else "N"
        dur_d = p.duration_s / 86400.0
        print(f"{p.phase_name:<15} {ok:<4} {p.delta_v_used_km_s:<12.4f} {p.fuel_consumed_kg:<10.3f} {dur_d:<12.1f}")
        if verbose:
            for ev in p.events:
                print(f"  -> {ev}")
            if p.notes:
                print(f"  NOTE: {p.notes}")

    print(f"\nScoring breakdown:")
    for k, v in report.scoring_breakdown.items():
        print(f"  {k}: {v}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m sim.run_mission <mission_plan.json> [--verbose]")
        sys.exit(1)

    plan_path = sys.argv[1]
    verbose = "--verbose" in sys.argv

    with open(plan_path) as f:
        plan = json.load(f)

    print(f"Loading plan: {plan.get('mission_name', plan_path)}")
    print(f"  Departure: {plan.get('departure_date')}")
    print(f"  Total Δv:  {plan.get('total_delta_v_km_s')} km/s")
    print(f"  Phases:    {len(plan.get('phases', []))}")
    print()

    conops = convert_plan_to_conops(plan)
    print(f"CONOPS built: {len(conops.transfer.maneuvers)} transfer maneuvers")
    print(f"  Transfer Δv: {conops.transfer.total_delta_v_km_s:.4f} km/s")
    if conops.arrival.orbit_insertion_maneuver:
        print(f"  Arrival Δv:  {conops.arrival.orbit_insertion_maneuver.delta_v_km_s:.4f} km/s")
    print()

    spacecraft_config = plan.get("spacecraft")
    if spacecraft_config:
        print(f"  Spacecraft:  {spacecraft_config.get('mass_kg')} kg, ISP {spacecraft_config.get('isp_s')} s")
    print("Executing through sim engine...")
    report = execute_conops(conops, spacecraft_config=spacecraft_config)
    print()
    print_report(report, verbose=verbose)


if __name__ == "__main__":
    main()
