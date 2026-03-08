"""SimEngine — pure function that advances the universe by one step.

step(state, action, mission, phase) -> (new_state, observation)

All physics calls go through spacecraft_sim. No mutation.
"""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import timedelta

import numpy as np

from spacecraft_sim import (
    AstronomicalData,
    CelestialBody,
    InterplanetaryTrajectories,
    LagrangeCoefficients,
    ThreeDimensionalOrbit,
)

from sim.state import (
    ActionType,
    AgentAction,
    BurnCommand,
    CelestialBodyState,
    CoastCommand,
    Event,
    EventType,
    HealthStatus,
    MissionState,
    Observation,
    OrbitState,
    OrbitType,
    PhaseState,
    PowerState,
    ProximityInfo,
    SimTime,
    SpacecraftState,
    SpacecraftStatus,
    SubsystemState,
    UniverseState,
)

AU_KM = 1.496e8  # 1 AU in km
G_0 = 9.80665e-3  # km/s² (for Tsiolkovsky in km/s units)

# Bodies to track in the sim (skip Moon — no JPL elements in tools)
TRACKED_BODIES = [
    CelestialBody.MERCURY, CelestialBody.VENUS, CelestialBody.EARTH,
    CelestialBody.MARS, CelestialBody.JUPITER, CelestialBody.SATURN,
    CelestialBody.URANUS, CelestialBody.NEPTUNE,
]


# ---------------------------------------------------------------------------
# Body state computation
# ---------------------------------------------------------------------------

def _compute_body_state(body: CelestialBody, epoch) -> CelestialBodyState:
    """Compute celestial body state at a given epoch."""
    if body == CelestialBody.SUN:
        return CelestialBodyState(
            body=CelestialBody.SUN,
            position_km=(0.0, 0.0, 0.0),
            velocity_km_s=(0.0, 0.0, 0.0),
            mu_km3_s2=AstronomicalData.gravitational_parameter(CelestialBody.SUN),
            radius_km=AstronomicalData.equatiorial_radius(CelestialBody.SUN),
            soi_km=float("inf"),
            orbital_elements=None,
        )

    if body == CelestialBody.MOON:
        raise ValueError("Moon ephemeris not supported (no JPL elements in tools)")

    r_v = InterplanetaryTrajectories.ephemeris(body, epoch)
    r, v = r_v[0], r_v[1]

    return CelestialBodyState(
        body=body,
        position_km=(float(r[0]), float(r[1]), float(r[2])),
        velocity_km_s=(float(v[0]), float(v[1]), float(v[2])),
        mu_km3_s2=AstronomicalData.gravitational_parameter(body),
        radius_km=AstronomicalData.equatiorial_radius(body),
        soi_km=AstronomicalData.sphere_of_influence(body),
        orbital_elements=None,  # Could derive from r,v if needed
    )




# ---------------------------------------------------------------------------
# Orbit classification
# ---------------------------------------------------------------------------

def _classify_orbit(e: float, r_p: float, body_radius: float) -> OrbitType:
    if r_p < body_radius:
        return OrbitType.SUBORBITAL
    if e < 0.001:
        return OrbitType.CIRCULAR
    if e < 1.0:
        return OrbitType.ELLIPTICAL
    if abs(e - 1.0) < 0.001:
        return OrbitType.PARABOLIC
    return OrbitType.HYPERBOLIC


def _compute_orbit_state(
    r: np.ndarray,
    v: np.ndarray,
    ref_body: CelestialBody,
) -> OrbitState:
    """Derive orbital elements and parameters from state vector."""
    mu = AstronomicalData.gravitational_parameter(ref_body)
    radius = AstronomicalData.equatiorial_radius(ref_body)

    ThreeDimensionalOrbit.set_celestial_body(ref_body)
    oe = ThreeDimensionalOrbit.calculate_orbital_elements(r, v)

    # TwoBodyProblem.calculate_orbital_parameters has a numerical bug
    # for near-circular orbits (sqrt of tiny negative). Compute key
    # parameters directly from orbital elements instead.
    r_mag = float(np.linalg.norm(r))
    v_mag = float(np.linalg.norm(v))
    altitude = r_mag - radius
    epsilon = v_mag**2 / 2.0 - mu / r_mag  # specific energy

    e = oe.e
    a = oe.a if oe.a > 0 else -mu / (2.0 * epsilon) if epsilon != 0 else float("inf")

    if e < 1.0 and a > 0:
        period = 2.0 * math.pi * math.sqrt(a**3 / mu)
        r_p = a * (1.0 - e)
        r_a = a * (1.0 + e)
    else:
        period = float("inf")
        r_p = oe.h**2 / (mu * (1.0 + e)) if mu > 0 else 0.0
        r_a = float("inf")

    # Build a minimal OrbitalParameters (avoiding the buggy sqrt)
    from spacecraft_sim import OrbitalParameters
    op = OrbitalParameters(
        h=oe.h, epsilon=epsilon, e=e, T=period,
        r_a=r_a, r_p=r_p, a=a, b=a * math.sqrt(abs(1.0 - e**2)) if a > 0 and a != float("inf") else 0.0,
    )

    orbit_type = _classify_orbit(e, r_p, radius)

    return OrbitState(
        elements=oe,
        parameters=op,
        altitude_km=altitude,
        period_s=period,
        orbit_type=orbit_type,
    )


# ---------------------------------------------------------------------------
# Proximity computation
# ---------------------------------------------------------------------------

def _compute_proximity(
    sc_pos: np.ndarray,
    sc_vel: np.ndarray,
    bodies: tuple[CelestialBodyState, ...],
) -> tuple[ProximityInfo, ...]:
    """Compute proximity to all bodies, sorted by distance."""
    results = []
    for body_state in bodies:
        body_pos = np.array(body_state.position_km)
        body_vel = np.array(body_state.velocity_km_s)

        rel_pos = sc_pos - body_pos
        rel_vel = sc_vel - body_vel
        distance = float(np.linalg.norm(rel_pos))
        altitude = distance - body_state.radius_km

        # Closing speed: negative means approaching
        if distance > 0:
            closing = float(np.dot(rel_vel, rel_pos) / distance)
        else:
            closing = 0.0

        results.append(ProximityInfo(
            body=body_state.body,
            distance_km=distance,
            altitude_km=altitude,
            within_soi=distance < body_state.soi_km,
            closing_speed_km_s=closing,
        ))

    return tuple(sorted(results, key=lambda p: p.distance_km))


# ---------------------------------------------------------------------------
# Event detection
# ---------------------------------------------------------------------------

def _detect_events(
    old_proximity: tuple[ProximityInfo, ...] | None,
    new_proximity: tuple[ProximityInfo, ...],
    time: SimTime,
) -> list[Event]:
    """Detect events by comparing old and new state."""
    events: list[Event] = []

    old_soi = {p.body: p.within_soi for p in old_proximity} if old_proximity else {}

    for prox in new_proximity:
        was_in_soi = old_soi.get(prox.body, False)

        # SOI transitions
        if prox.within_soi and not was_in_soi:
            events.append(Event(
                type=EventType.SOI_ENTER,
                time=time,
                body=prox.body,
                details={"distance_km": prox.distance_km},
            ))
        elif not prox.within_soi and was_in_soi:
            events.append(Event(
                type=EventType.SOI_EXIT,
                time=time,
                body=prox.body,
                details={"distance_km": prox.distance_km},
            ))

        # Collision
        if prox.altitude_km <= 0:
            events.append(Event(
                type=EventType.COLLISION,
                time=time,
                body=prox.body,
                details={"altitude_km": prox.altitude_km},
            ))

    return events


# ---------------------------------------------------------------------------
# Subsystem updates (simplified models)
# ---------------------------------------------------------------------------

def _update_subsystems(
    old: SubsystemState,
    sc_pos_helio: np.ndarray,
    dt: float,
    burn_dv: float,
) -> SubsystemState:
    """Update subsystem states for one tick. Simple parametric models."""
    distance_au = float(np.linalg.norm(sc_pos_helio)) / AU_KM

    # Power: solar scales as 1/r²
    solar_input = old.power.solar_max_w / (distance_au ** 2) if distance_au > 0 else 0.0
    # Drain battery during eclipse or if load > solar
    load_w = 5.0  # cruise load
    if burn_dv > 0:
        load_w = 20.0  # burn operations
    net_w = solar_input - load_w
    # SOC change: net_w * dt(hours) / capacity_wh * 100%
    dt_hours = dt / 3600.0
    # Assume 38 Wh capacity (MarCO-X)
    soc_delta = (net_w * dt_hours / 38.0) * 100.0
    new_soc = max(0.0, min(100.0, old.power.battery_soc_pct + soc_delta))

    # Voltage model: linear with SOC (simplified)
    new_voltage = 9.0 + (new_soc / 100.0) * 3.0  # 9V at 0%, 12V at 100%

    power_status = _power_health(new_soc, new_voltage, solar_input)
    new_power = PowerState(
        status=power_status,
        battery_soc_pct=new_soc,
        battery_voltage_v=new_voltage,
        solar_input_w=solar_input,
        solar_max_w=old.power.solar_max_w,
        distance_au=distance_au,
        in_eclipse=old.power.in_eclipse,  # TODO: eclipse detection
    )

    # Thermal: simplified — temperature drifts toward equilibrium
    # Equilibrium ~20°C near Earth, colder farther out
    equil_c = 20.0 / (distance_au ** 0.5) if distance_au > 0 else 20.0
    tau = 3600.0  # thermal time constant [s]
    alpha = 1.0 - math.exp(-dt / tau) if dt > 0 else 0.0
    new_prop_temp = old.thermal.propulsion_temp_c + alpha * (equil_c - old.thermal.propulsion_temp_c)
    new_batt_temp = old.thermal.battery_temp_c + alpha * (equil_c - old.thermal.battery_temp_c)
    new_elec_temp = old.thermal.electronics_temp_c + alpha * (equil_c + 5.0 - old.thermal.electronics_temp_c)

    thermal_status = _thermal_health(new_prop_temp, new_batt_temp, new_elec_temp)
    new_thermal = replace(
        old.thermal,
        status=thermal_status,
        propulsion_temp_c=new_prop_temp,
        battery_temp_c=new_batt_temp,
        electronics_temp_c=new_elec_temp,
    )

    # Propulsion: can_fire gates
    inhibit = _check_fire_inhibit(new_prop_temp, new_voltage, old.adcs.pointing_error_deg, old.propulsion.fuel_kg)
    new_propulsion = replace(
        old.propulsion,
        can_fire=inhibit is None,
        fire_inhibit_reason=inhibit,
    )

    # Comms: rate scales as 1/r²
    rate = min(256.0, 8.0 / (distance_au ** 2)) if distance_au > 0 else 256.0
    new_comms = replace(
        old.comms,
        status=HealthStatus.GREEN if rate > 2.0 else HealthStatus.YELLOW if rate > 0.5 else HealthStatus.RED,
        downlink_rate_kbps=rate,
        link_margin_db=max(0.0, 10.0 * math.log10(rate / 0.1)) if rate > 0 else 0.0,
    )

    # ADCS: RW saturation drifts up slowly, resets on desaturate
    new_adcs = old.adcs

    return SubsystemState(
        power=new_power,
        thermal=new_thermal,
        propulsion=new_propulsion,
        comms=new_comms,
        adcs=new_adcs,
    )


def _power_health(soc: float, voltage: float, solar: float) -> HealthStatus:
    if soc < 20.0:
        return HealthStatus.EMERGENCY
    if soc < 30.0 or voltage < 9.5 or solar < 5.0:
        return HealthStatus.RED
    if soc < 60.0 or voltage < 11.0 or solar < 10.0:
        return HealthStatus.YELLOW
    return HealthStatus.GREEN


def _thermal_health(prop_c: float, batt_c: float, elec_c: float) -> HealthStatus:
    if prop_c < -30.0 or prop_c > 55.0:
        return HealthStatus.RED
    if batt_c < -20.0 or batt_c > 60.0:
        return HealthStatus.RED
    if elec_c < -40.0 or elec_c > 85.0:
        return HealthStatus.RED
    if prop_c < -20.0 or prop_c > 45.0:
        return HealthStatus.YELLOW
    if batt_c < -10.0 or batt_c > 50.0:
        return HealthStatus.YELLOW
    return HealthStatus.GREEN


def _check_fire_inhibit(
    prop_temp: float, voltage: float, pointing_err: float, fuel_kg: float,
) -> str | None:
    if fuel_kg <= 0:
        return "no_fuel"
    if prop_temp < -30.0:
        return f"prop_temp_low ({prop_temp:.1f}°C < -30°C)"
    if voltage < 9.0:
        return f"voltage_low ({voltage:.1f}V < 9.0V)"
    if pointing_err > 0.5:
        return f"pointing_error ({pointing_err:.3f}° > 0.5°)"
    return None


# ---------------------------------------------------------------------------
# Core step function
# ---------------------------------------------------------------------------

def step(
    state: UniverseState,
    action: AgentAction,
    mission: MissionState,
    phase: PhaseState,
) -> tuple[UniverseState, Observation]:
    """Advance the universe by one step given an agent action.

    Returns new UniverseState and an Observation for the agent.
    """
    sc = state.spacecraft[0]  # Single spacecraft for now
    r = np.array(sc.position_km)
    v = np.array(sc.velocity_km_s)
    ref_body = sc.reference_body
    dt = 0.0
    burn_dv = 0.0
    new_events: list[Event] = []

    dm = 0.0  # Mass consumed by this action

    # --- Process action ---
    if action.type == ActionType.BURN and isinstance(action.payload, BurnCommand):
        burn = action.payload
        if not sc.subsystems.propulsion.can_fire:
            new_events.append(Event(
                type=EventType.BURN_COMPLETE,
                time=state.time,
                body=None,
                details={"inhibited": True, "reason": sc.subsystems.propulsion.fire_inhibit_reason},
            ))
        else:
            dv_vec = np.array(burn.direction)
            dv_norm = np.linalg.norm(dv_vec)
            if dv_norm > 0:
                dv_vec = dv_vec / dv_norm * burn.magnitude_km_s
            v = v + dv_vec
            burn_dv = burn.magnitude_km_s

            # Fuel consumption (Tsiolkovsky)
            dm = sc.mass_kg * (1.0 - math.exp(-burn_dv / (sc.isp_s * G_0)))
            dm = min(dm, sc.fuel_kg)  # Can't burn more fuel than we have

            new_events.append(Event(
                type=EventType.BURN_COMPLETE,
                time=state.time,
                body=None,
                details={"dv_km_s": burn_dv, "dm_kg": dm},
            ))

            dt = 1.0  # Burns are near-instantaneous; advance 1s

    elif action.type == ActionType.COAST and isinstance(action.payload, CoastCommand):
        dt = action.payload.duration_s

    elif action.type == ActionType.TCM and isinstance(action.payload, BurnCommand):
        # TCM is just a small burn
        burn = action.payload
        if sc.subsystems.propulsion.can_fire:
            dv_vec = np.array(burn.direction)
            dv_norm = np.linalg.norm(dv_vec)
            if dv_norm > 0:
                dv_vec = dv_vec / dv_norm * burn.magnitude_km_s
            v = v + dv_vec
            burn_dv = burn.magnitude_km_s
            dm = sc.mass_kg * (1.0 - math.exp(-burn_dv / (sc.isp_s * G_0)))
            dm = min(dm, sc.fuel_kg)
            dt = 1.0
        else:
            dm = 0.0

    elif action.type == ActionType.DESATURATE:
        # Small delta-v cost for RW desaturation
        burn_dv = 0.0001  # ~0.1 m/s
        dm = sc.mass_kg * (1.0 - math.exp(-burn_dv / (sc.isp_s * G_0)))
        dm = min(dm, sc.fuel_kg)
        dt = 60.0  # Takes about a minute

    else:
        # DEPLOY, CHECKOUT, SAFE_MODE, DOWNLINK, etc. — no physics change
        dt = 60.0  # These take ~1 minute of sim time
        dm = 0.0

    # --- SOI check: switch reference body if spacecraft escapes/enters ---
    if ref_body != CelestialBody.SUN:
        soi_radius = AstronomicalData.sphere_of_influence(ref_body)
        r_mag = float(np.linalg.norm(r))
        if r_mag > soi_radius:
            # Escaped current body — convert to heliocentric frame
            for bs in state.bodies:
                if bs.body == ref_body:
                    r = r + np.array(bs.position_km)
                    v = v + np.array(bs.velocity_km_s)
                    break
            ref_body = CelestialBody.SUN

    # --- Propagate orbit if coasting ---
    if dt > 0:
        LagrangeCoefficients.mu = AstronomicalData.gravitational_parameter(ref_body)
        r_new, v_new = LagrangeCoefficients.calculate_position_velocity_by_time(r, v, dt)
        r = np.array(r_new)
        v = np.array(v_new)

    # --- Advance time ---
    new_time = SimTime(
        elapsed_s=state.time.elapsed_s + dt,
        epoch=state.time.epoch + timedelta(seconds=dt),
        step=state.time.step + 1,
    )

    # --- Update body positions ---
    new_bodies = tuple(
        _compute_body_state(bs.body, new_time.epoch)
        for bs in state.bodies
    )

    # --- SOI entry: switch from heliocentric to body-centered ---
    if ref_body == CelestialBody.SUN:
        for bs in new_bodies:
            if bs.body == CelestialBody.SUN:
                continue
            body_pos = np.array(bs.position_km)
            body_vel = np.array(bs.velocity_km_s)
            rel_pos = r - body_pos
            dist = float(np.linalg.norm(rel_pos))
            if dist < bs.soi_km:
                r = rel_pos
                v = v - body_vel
                ref_body = bs.body
                break

    # --- Compute new orbit ---
    new_orbit = _compute_orbit_state(r, v, ref_body)

    # --- Compute proximity ---
    # For proximity, we need spacecraft position in heliocentric frame
    # If ref_body != SUN, offset by body position
    sc_pos_helio = r
    if ref_body != CelestialBody.SUN:
        for bs in new_bodies:
            if bs.body == ref_body:
                sc_pos_helio = r + np.array(bs.position_km)
                break

    new_proximity = _compute_proximity(
        sc_pos_helio, v, new_bodies,
    )

    # --- Detect events ---
    old_proximity = _compute_proximity(
        np.array(sc.position_km), np.array(sc.velocity_km_s), state.bodies,
    ) if state.time.step > 0 else None

    detected_events = _detect_events(old_proximity, new_proximity, new_time)
    new_events.extend(detected_events)

    # --- Check for fuel depletion ---
    new_fuel = sc.fuel_kg - dm
    if new_fuel <= 0 and sc.fuel_kg > 0:
        new_fuel = 0.0
        new_events.append(Event(
            type=EventType.FUEL_DEPLETED,
            time=new_time,
            body=None,
            details={},
        ))

    # --- Update spacecraft status ---
    new_status = sc.status
    if any(e.type == EventType.COLLISION for e in new_events):
        new_status = SpacecraftStatus.CRASHED
    elif new_fuel <= 0 and sc.status == SpacecraftStatus.NOMINAL:
        new_status = SpacecraftStatus.OUT_OF_FUEL

    # --- Update subsystems ---
    new_subsystems = _update_subsystems(
        sc.subsystems, sc_pos_helio, dt, burn_dv,
    )
    # Sync fuel in propulsion state
    new_propulsion = replace(
        new_subsystems.propulsion,
        fuel_kg=new_fuel,
        total_impulse_remaining_ns=max(0.0, new_fuel * sc.isp_s * G_0 * 1000.0),
    )
    new_subsystems = replace(new_subsystems, propulsion=new_propulsion)

    # --- Build new spacecraft state ---
    new_sc = SpacecraftState(
        id=sc.id,
        position_km=(float(r[0]), float(r[1]), float(r[2])),
        velocity_km_s=(float(v[0]), float(v[1]), float(v[2])),
        mass_kg=sc.mass_kg - dm,
        dry_mass_kg=sc.dry_mass_kg,
        fuel_kg=new_fuel,
        isp_s=sc.isp_s,
        reference_body=ref_body,
        orbit=new_orbit,
        subsystems=new_subsystems,
        status=new_status,
    )

    # --- Build new universe state ---
    all_events = tuple(new_events)
    new_state = UniverseState(
        time=new_time,
        bodies=new_bodies,
        spacecraft=(new_sc,),
        events=all_events,
    )

    # --- Update mission tracking ---
    new_mission = replace(
        mission,
        delta_v_used_km_s=mission.delta_v_used_km_s + burn_dv,
        impulse_used_ns=mission.impulse_used_ns + (dm * sc.isp_s * G_0 * 1000.0),
        elapsed_s=new_time.elapsed_s,
    )

    # --- Build observation ---
    observation = Observation(
        time=new_time,
        spacecraft=new_sc,
        proximity=new_proximity,
        events=all_events,
        mission=new_mission,
        phase=phase,
    )

    return new_state, observation
