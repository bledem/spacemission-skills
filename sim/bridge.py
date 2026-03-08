"""Bridge: convert a flat mission_plan.json into a CONOPS for the executor.

Usage:
    from sim.bridge import convert_plan_to_conops
    conops = convert_plan_to_conops(plan_dict)
"""

from __future__ import annotations

from datetime import datetime, timezone

from spacecraft_sim import AstronomicalData, CelestialBody

from sim.conops import (
    CONOPS,
    ArrivalPhase,
    ArrivalStrategy,
    CruisePhase,
    DisposalStrategy,
    EarlyOpsPhase,
    EndOfLifePhase,
    InjectionOrbit,
    LaunchPhase,
    PrimaryOpsPhase,
    TransferManeuver,
    TransferPhase,
    TransferType,
)


R_EARTH_KM = AstronomicalData.equatiorial_radius(CelestialBody.EARTH)


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(
        hour=12, tzinfo=timezone.utc
    )


def _validate_plan(plan: dict) -> None:
    """Validate required fields. Raises ValueError with specifics."""
    if "phases" not in plan or not plan["phases"]:
        raise ValueError("Plan must have a non-empty 'phases' list")
    if "departure_date" not in plan:
        raise ValueError("Plan must have 'departure_date'")
    if "total_delta_v_km_s" not in plan:
        raise ValueError("Plan must have 'total_delta_v_km_s'")

    phase_names = {p.get("phase") for p in plan["phases"]}
    if "earth_departure" not in phase_names:
        raise ValueError("Plan must have an 'earth_departure' phase")

    for i, phase in enumerate(plan["phases"]):
        for key in ("phase", "date", "delta_v_km_s"):
            if key not in phase:
                raise ValueError(f"Phase {i} missing required key '{key}'")
        if phase["delta_v_km_s"] < 0:
            raise ValueError(
                f"Phase {i} has negative delta_v: {phase['delta_v_km_s']}"
            )


def _phase_by_name(phases: list[dict], name: str) -> dict | None:
    for p in phases:
        if p.get("phase") == name:
            return p
    return None


def _direction_for_phase(phase: dict) -> str:
    """Get burn direction from phase, defaulting by phase type."""
    if "direction" in phase:
        return phase["direction"]
    name = phase.get("phase", "")
    if "departure" in name:
        return "prograde"
    if "arrival" in name:
        return "retrograde"
    return "prograde"


def convert_plan_to_conops(plan: dict) -> CONOPS:
    """Convert a flat mission plan dict to a CONOPS dataclass."""
    _validate_plan(plan)

    phases = plan["phases"]
    dep_phase = _phase_by_name(phases, "earth_departure")
    assert dep_phase is not None  # validated above
    arr_phase = _phase_by_name(phases, "earth_arrival")

    dep_date = _parse_date(plan["departure_date"])
    ret_date = _parse_date(plan.get("return_date", ""))  if plan.get("return_date") else None
    if ret_date is None and arr_phase:
        ret_date = _parse_date(arr_phase["date"])
    if ret_date is None:
        last_phase = phases[-1]
        ret_date = _parse_date(last_phase["date"])

    duration_days = (ret_date - dep_date).days

    # --- Parking orbit ---
    parking_r = dep_phase.get("parking_orbit_radius_km", 6678.0)
    altitude_km = parking_r - R_EARTH_KM
    inclination_deg = dep_phase.get("inclination_deg", 28.5)

    # --- Launch ---
    launch = LaunchPhase(
        launch_site="Cape Canaveral SLC-41",
        launch_vehicle="Atlas V 401",
        target_injection_orbit=InjectionOrbit(
            type="LEO",
            altitude_km=altitude_km,
            apoapsis_km=None,
            inclination_deg=inclination_deg,
        ),
        launch_direction=f"Due east, {inclination_deg} deg inclination",
        launch_date=dep_date,
        launch_window_days=21,
    )

    # --- Early Ops ---
    early_ops = EarlyOpsPhase(
        separation_orbit=launch.target_injection_orbit,
        post_separation_actions=("comms", "adcs", "propulsion"),
        transfer_readiness_condition="All subsystems commissioned",
        duration_hours=24.0,
    )

    # --- Transfer: pack all burns as maneuvers ---
    maneuvers: list[TransferManeuver] = []
    for phase in phases:
        name = phase["phase"]
        if name == "earth_arrival":
            continue  # arrival burn handled separately
        maneuvers.append(TransferManeuver(
            name=name,
            date=_parse_date(phase["date"]),
            delta_v_km_s=phase["delta_v_km_s"],
            direction=_direction_for_phase(phase),
            location="computed",
            pre_burn_orbit="see transfer_orbit in plan",
            post_burn_orbit="see transfer_orbit in plan",
        ))

    # Determine target body from plan
    target_body_str = dep_phase.get("to_body", "MARS")
    target_body_map = {
        "MARS": "Mars", "JUPITER": "Jupiter", "SATURN": "Saturn",
        "VENUS": "Venus", "MERCURY": "Mercury",
    }
    arrival_body = target_body_map.get(target_body_str, target_body_str)

    total_transfer_dv = sum(m.delta_v_km_s for m in maneuvers)
    transfer_days = (ret_date - dep_date).days if ret_date else duration_days

    transfer = TransferPhase(
        transfer_type=TransferType.LAMBERT,
        maneuvers=tuple(maneuvers),
        propulsion_source="bipropellant",
        transfer_duration_days=float(transfer_days),
        departure_body="Earth",
        arrival_body=arrival_body,
        departure_date=dep_date,
        arrival_date=ret_date,
        total_delta_v_km_s=total_transfer_dv,
    )

    # --- Cruise (minimal — coasting handled by transfer maneuver gaps) ---
    cruise = CruisePhase(
        cruise_mode="spin-stabilized",
        nav_strategy="DSN tracking",
        tcm_schedule=(),
        critical_constraints=("solar power > 5W",),
        duration_days=1.0,  # minimal; transfer handles the real coasting
        dsn_contact_schedule="Weekly 30-min passes",
    )

    # --- Arrival ---
    if arr_phase:
        arrival_maneuver = TransferManeuver(
            name="earth_arrival",
            date=_parse_date(arr_phase["date"]),
            delta_v_km_s=arr_phase["delta_v_km_s"],
            direction=_direction_for_phase(arr_phase),
            location="periapsis",
            pre_burn_orbit="hyperbolic approach",
            post_burn_orbit="captured orbit",
        )
        arrival = ArrivalPhase(
            arrival_strategy=ArrivalStrategy.ORBIT_INSERTION,
            orbit_insertion_maneuver=arrival_maneuver,
            initial_captured_orbit=f"{altitude_km:.0f} km circular",
            final_operational_orbit=f"{altitude_km:.0f} km circular",
            approach_nav="DSN tracking",
            closest_approach_km=parking_r,
        )
    else:
        arrival = ArrivalPhase(
            arrival_strategy=ArrivalStrategy.FLYBY,
            orbit_insertion_maneuver=None,
            initial_captured_orbit=None,
            final_operational_orbit=None,
            approach_nav="DSN tracking",
            closest_approach_km=500.0,
        )

    # --- Primary Ops ---
    primary_ops = PrimaryOpsPhase(
        science_orbit=f"{altitude_km:.0f} km circular",
        observation_strategy="Standard science ops",
        primary_payloads=("wide-angle camera",),
        mission_success_metric="Mission plan executed",
        duration_days=30.0,
    )

    # --- End of Life ---
    end_of_life = EndOfLifePhase(
        end_condition="Mission duration complete",
        disposal_strategy=DisposalStrategy.HELIOCENTRIC,
        final_spacecraft_state="Passivated in heliocentric orbit",
        disposal_delta_v_km_s=0.0,
    )

    # --- Total delta-v ---
    total_dv = plan["total_delta_v_km_s"]
    allocated_dv = total_transfer_dv + (arr_phase["delta_v_km_s"] if arr_phase else 0.0)

    return CONOPS(
        mission_name=plan.get("mission_name", "Mission"),
        mission_objective=plan.get("mission_objective", "Execute mission plan"),
        spacecraft_id="marco-x",
        spacecraft_config="MarCO-X 6U CubeSat",
        total_delta_v_budget_km_s=total_dv,
        total_delta_v_allocated_km_s=allocated_dv,
        delta_v_margin_km_s=max(0.0, total_dv - allocated_dv),
        mission_start=dep_date,
        mission_end=ret_date,
        mission_duration_days=float(duration_days),
        launch=launch,
        early_ops=early_ops,
        transfer=transfer,
        cruise=cruise,
        arrival=arrival,
        primary_ops=primary_ops,
        extended_ops=None,
        end_of_life=end_of_life,
    )
