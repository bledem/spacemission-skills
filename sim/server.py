"""WebSocket server — runs the sim tick loop and pushes state to the viewer.

Usage:
    python -m sim.server [--port 8765] [--tick-hz 1]

The server:
1. Initializes the universe with a spacecraft in LEO
2. Waits for viewer connection
3. Runs tick loop: agent acts → engine.step() → push state via WS
4. Viewer renders each state frame
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum

import numpy as np

from spacecraft_sim import (
    AstronomicalData,
    CelestialBody,
)

from sim.engine import TRACKED_BODIES, _compute_body_state, _compute_orbit_state, step
from sim.state import (
    ADCSMode,
    ADCSState,
    ActionType,
    AgentAction,
    CoastCommand,
    CommsState,
    HealthStatus,
    MissionPhase,
    MissionState,
    Observation,
    PhaseState,
    PowerState,
    PropulsionState,
    SimTime,
    SpacecraftState,
    SpacecraftStatus,
    SubsystemState,
    ThermalState,
    UniverseState,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON serializer for dataclasses with enums/datetime
# ---------------------------------------------------------------------------

class StateEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Enum):
            return o.value
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.floating, np.integer)):
            return float(o)
        if isinstance(o, float) and (math.isinf(o) or math.isnan(o)):
            return None
        return super().default(o)


def state_to_json(state: UniverseState) -> str:
    return json.dumps(asdict(state), cls=StateEncoder)


def observation_to_json(obs: Observation) -> str:
    return json.dumps(asdict(obs), cls=StateEncoder)


# ---------------------------------------------------------------------------
# Initial state factory
# ---------------------------------------------------------------------------

def create_initial_state(
    epoch: datetime | None = None,
    altitude_km: float = 300.0,
    inclination_deg: float = 28.5,
    wet_mass_kg: float = 14.0,
    dry_mass_kg: float = 8.6,
    fuel_kg: float = 5.4,
    isp_s: float = 40.0,
) -> tuple[UniverseState, MissionState, PhaseState]:
    """Create initial universe state with spacecraft in Earth LEO."""
    if epoch is None:
        epoch = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    time = SimTime(elapsed_s=0.0, epoch=epoch, step=0)

    # --- Celestial bodies ---
    body_states = [_compute_body_state(CelestialBody.SUN, epoch)]
    for body in TRACKED_BODIES:
        body_states.append(_compute_body_state(body, epoch))
    bodies = tuple(body_states)

    # --- Spacecraft in LEO ---
    mu_earth = AstronomicalData.gravitational_parameter(CelestialBody.EARTH)
    r_earth = AstronomicalData.equatiorial_radius(CelestialBody.EARTH)
    r_orbit = r_earth + altitude_km
    v_circular = math.sqrt(mu_earth / r_orbit)

    # Inclined circular orbit at ascending node (theta=0, omega=0)
    # Position in orbital plane x-axis, velocity in y-axis, rotated by inclination
    i_rad = math.radians(inclination_deg)
    # At ascending node: r along x, v along y rotated by inclination about x-axis
    r_vec = (r_orbit, 0.0, 0.0)
    v_vec = (0.0, v_circular * math.cos(i_rad), v_circular * math.sin(i_rad))

    # Verify: |v| should equal v_circular
    v_mag = math.sqrt(v_vec[0]**2 + v_vec[1]**2 + v_vec[2]**2)
    assert abs(v_mag - v_circular) < 1e-10, f"Velocity magnitude mismatch: {v_mag} vs {v_circular}"

    r_np = np.array(r_vec)
    v_np = np.array(v_vec)

    orbit = _compute_orbit_state(r_np, v_np, CelestialBody.EARTH)

    # --- Subsystems (nominal startup) ---
    subsystems = SubsystemState(
        power=PowerState(
            status=HealthStatus.GREEN,
            battery_soc_pct=95.0,
            battery_voltage_v=12.0,
            solar_input_w=72.0,
            solar_max_w=72.0,
            distance_au=1.0,
            in_eclipse=False,
        ),
        thermal=ThermalState(
            status=HealthStatus.GREEN,
            propulsion_temp_c=20.0,
            battery_temp_c=22.0,
            electronics_temp_c=25.0,
        ),
        propulsion=PropulsionState(
            status=HealthStatus.GREEN,
            fuel_kg=fuel_kg,
            total_impulse_remaining_ns=fuel_kg * isp_s * 9.80665,  # N·s
            thrust_n=0.025,
            isp_s=isp_s,
            can_fire=True,
            fire_inhibit_reason=None,
        ),
        comms=CommsState(
            status=HealthStatus.GREEN,
            link_margin_db=15.0,
            downlink_rate_kbps=256.0,
            data_buffer_fill_pct=0.0,
            in_blackout=False,
            dsn_pass_active=True,
        ),
        adcs=ADCSState(
            status=HealthStatus.GREEN,
            pointing_error_deg=0.005,
            mode=ADCSMode.FINE_REFERENCE,
            rw_saturation_pct=5.0,
        ),
    )

    sc = SpacecraftState(
        id="marco-x",
        position_km=r_vec,
        velocity_km_s=v_vec,
        mass_kg=wet_mass_kg,
        dry_mass_kg=dry_mass_kg,
        fuel_kg=fuel_kg,
        isp_s=isp_s,
        reference_body=CelestialBody.EARTH,
        orbit=orbit,
        subsystems=subsystems,
        status=SpacecraftStatus.NOMINAL,
    )

    universe = UniverseState(
        time=time,
        bodies=bodies,
        spacecraft=(sc,),
        events=(),
    )

    mission = MissionState(
        objective="Mars flyby — maximize science return while staying within delta-v budget",
        target_body=CelestialBody.MARS,
        target_orbit=None,
        delta_v_used_km_s=0.0,
        delta_v_budget_km_s=0.054,  # ~54 m/s for MarCO-X
        impulse_used_ns=0.0,
        impulse_budget_ns=755.0,
        elapsed_s=0.0,
        max_duration_s=365.25 * 24 * 3600 * 2,  # 2 years
    )

    phase = PhaseState(
        current_phase=MissionPhase.LAUNCH_DEPLOY,
        phase_start_time=time,
        phase_elapsed_s=0.0,
        entry_criteria_met=("sim_start",),
        exit_criteria=("arrays_deployed", "attitude_acquired", "dsn_contact"),
        available_actions=(ActionType.DEPLOY, ActionType.CHECKOUT, ActionType.COAST),
    )

    return universe, mission, phase


# ---------------------------------------------------------------------------
# WebSocket server
# ---------------------------------------------------------------------------

async def run_server(port: int = 8765, tick_hz: float = 1.0):
    """Run the sim server. Pushes state to all connected viewers."""
    try:
        import websockets
    except ImportError:
        logger.error("websockets not installed. Run: uv pip install websockets")
        return

    state, mission, phase = create_initial_state()
    clients: set = set()
    tick_interval = 1.0 / tick_hz

    async def handler(ws):
        clients.add(ws)
        logger.info(f"Viewer connected ({len(clients)} total)")
        try:
            # Send current state immediately on connect
            await ws.send(state_to_json(state))
            # Keep connection alive, receive agent actions (future)
            async for msg in ws:
                logger.debug(f"Received from client: {msg[:100]}")
        finally:
            clients.discard(ws)
            logger.info(f"Viewer disconnected ({len(clients)} total)")

    async def tick_loop():
        nonlocal state, mission, phase

        logger.info(f"Sim tick loop started at {tick_hz} Hz")
        while True:
            await asyncio.sleep(tick_interval)

            # Default action: coast for 1 orbital period / 100 steps
            # This gives ~90 second chunks for LEO
            coast_dt = 90.0  # seconds of sim time per tick

            action = AgentAction(
                type=ActionType.COAST,
                payload=CoastCommand(duration_s=coast_dt),
            )

            state, obs = step(state, action, mission, phase)
            mission = obs.mission

            # Broadcast to all connected viewers
            msg = state_to_json(state)
            if clients:
                await asyncio.gather(
                    *(client.send(msg) for client in clients),
                    return_exceptions=True,
                )

            if state.time.step % 100 == 0:
                sc = state.spacecraft[0]
                logger.info(
                    f"Step {state.time.step} | "
                    f"T+{state.time.elapsed_s:.0f}s | "
                    f"Alt: {sc.orbit.altitude_km:.1f} km | "
                    f"Fuel: {sc.fuel_kg:.3f} kg | "
                    f"SOC: {sc.subsystems.power.battery_soc_pct:.1f}%"
                )

    async with websockets.serve(handler, "localhost", port):
        logger.info(f"Sim server listening on ws://localhost:{port}")
        await tick_loop()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Space Mission Sim Server")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--tick-hz", type=float, default=1.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run_server(port=args.port, tick_hz=args.tick_hz))
