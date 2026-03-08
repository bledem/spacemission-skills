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
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum

import numpy as np

from spacecraft_sim import (
    AstronomicalData,
    CelestialBody,
)

from sim.bridge import convert_plan_to_conops
from sim.engine import TRACKED_BODIES, _compute_body_state, _compute_orbit_state, step
from sim.state import (
    ADCSMode,
    ADCSState,
    ActionType,
    AgentAction,
    BurnCommand,
    CoastCommand,
    CommsState,
    EventType,
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


def _sanitize_floats(obj):
    """Replace inf/nan with None recursively (not valid JSON)."""
    if isinstance(obj, float):
        if math.isinf(obj) or math.isnan(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_floats(v) for v in obj]
    return obj


def state_to_json(state: UniverseState) -> str:
    return json.dumps(_sanitize_floats(asdict(state)), cls=StateEncoder)


def observation_to_json(obs: Observation) -> str:
    return json.dumps(_sanitize_floats(asdict(obs)), cls=StateEncoder)


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

def parse_agent_action(raw: str) -> AgentAction | None:
    """Parse a JSON message into an AgentAction. Returns None on failure."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON from agent: {raw[:200]}")
        return None

    action_type_str = data.get("type")
    if not action_type_str:
        return None

    try:
        action_type = ActionType(action_type_str)
    except ValueError:
        logger.warning(f"Unknown action type: {action_type_str}")
        return None

    payload_data = data.get("payload")
    payload = None

    if action_type == ActionType.BURN and payload_data:
        payload = BurnCommand(
            direction=tuple(payload_data["direction"]),
            magnitude_km_s=payload_data["magnitude_km_s"],
        )
    elif action_type == ActionType.COAST and payload_data:
        stop_event = None
        if payload_data.get("stop_at_event"):
            try:
                stop_event = EventType(payload_data["stop_at_event"])
            except ValueError:
                pass
        payload = CoastCommand(
            duration_s=payload_data.get("duration_s", 90.0),
            stop_at_event=stop_event,
        )

    return AgentAction(type=action_type, payload=payload)


@dataclass
class _PlannedManeuver:
    """A burn to execute at a specific epoch during plan replay."""
    epoch: datetime
    direction: str  # "prograde", "retrograde", etc.
    magnitude_km_s: float


def _conops_to_plan(conops) -> list[_PlannedManeuver]:
    """Extract the ordered list of maneuvers from a CONOPS."""
    maneuvers: list[_PlannedManeuver] = []
    for m in conops.transfer.maneuvers:
        maneuvers.append(_PlannedManeuver(
            epoch=m.date, direction=m.direction, magnitude_km_s=m.delta_v_km_s,
        ))
    if conops.arrival.orbit_insertion_maneuver:
        m = conops.arrival.orbit_insertion_maneuver
        maneuvers.append(_PlannedManeuver(
            epoch=m.date, direction=m.direction, magnitude_km_s=m.delta_v_km_s,
        ))
    return maneuvers


def _resolve_direction(
    direction: str, velocity: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Convert direction string to unit vector relative to current velocity."""
    vx, vy, vz = velocity
    v_mag = math.sqrt(vx**2 + vy**2 + vz**2)
    if v_mag == 0:
        return (1.0, 0.0, 0.0)
    pro = (vx / v_mag, vy / v_mag, vz / v_mag)
    d = direction.lower()
    if "retrograde" in d:
        return (-pro[0], -pro[1], -pro[2])
    if "normal" in d:
        return (0.0, 0.0, 1.0)
    return pro  # prograde default


async def run_server(port: int = 8765, tick_hz: float = 1.0, time_warp: float = 1.0):
    """Run the sim server. Pushes state to all connected viewers.

    Args:
        time_warp: Ratio of sim time to real time. 1.0 = real-time,
                   60.0 = 1 real second = 1 sim minute,
                   3600.0 = 1 real second = 1 sim hour.
    """
    try:
        import websockets
    except ImportError:
        logger.error("websockets not installed. Run: uv pip install websockets")
        return

    state, mission, phase = create_initial_state()
    latest_obs_json: str | None = None  # cached for agent handshake
    viewers: set = set()
    agents: set = set()
    action_queue: asyncio.Queue[AgentAction] = asyncio.Queue()
    plan_queue: asyncio.Queue[dict] = asyncio.Queue()
    tick_interval = 1.0 / tick_hz

    async def handler(ws):
        nonlocal latest_obs_json
        # First message determines role: {"role": "agent"} or default viewer
        role = "viewer"
        viewers.add(ws)
        logger.info(f"Client connected ({len(viewers)} viewers, {len(agents)} agents)")

        try:
            # Send current state immediately (viewers need this)
            await ws.send(state_to_json(state))

            async for raw in ws:
                # Check for role handshake
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                # Load mission plan
                if msg.get("type") == "load_plan" and "plan" in msg:
                    logger.info("Received mission plan from viewer")
                    await plan_queue.put(msg["plan"])
                    await ws.send(json.dumps({"type": "plan_ack", "status": "ok"}))
                    continue

                if msg.get("role") == "agent" and role != "agent":
                    role = "agent"
                    viewers.discard(ws)
                    agents.add(ws)
                    logger.info(f"Client upgraded to agent ({len(viewers)} viewers, {len(agents)} agents)")
                    # Send latest observation so agent has initial state
                    if latest_obs_json:
                        await ws.send(latest_obs_json)
                    continue

                # Agent action
                if role == "agent":
                    action = parse_agent_action(raw)
                    if action:
                        await action_queue.put(action)
                        logger.debug(f"Queued action: {action.type.value}")
        finally:
            viewers.discard(ws)
            agents.discard(ws)
            logger.info(f"Client disconnected ({len(viewers)} viewers, {len(agents)} agents)")

    async def _broadcast_state(s):
        """Push state to all viewers."""
        state_msg = state_to_json(s)
        if viewers:
            await asyncio.gather(
                *(v.send(state_msg) for v in viewers),
                return_exceptions=True,
            )

    async def _execute_plan(plan: dict):
        """Execute a mission plan through the sim, broadcasting each step."""
        nonlocal state, mission, phase, latest_obs_json

        logger.info(f"Executing plan: {plan.get('mission_name', 'unknown')}")
        conops = convert_plan_to_conops(plan)

        # Re-initialize state from the plan's epoch/orbit
        state, mission, phase = create_initial_state(
            epoch=conops.mission_start,
            altitude_km=conops.launch.target_injection_orbit.altitude_km,
            inclination_deg=conops.launch.target_injection_orbit.inclination_deg,
        )
        await _broadcast_state(state)

        maneuvers = _conops_to_plan(conops)
        end_epoch = conops.mission_end
        maneuver_idx = 0
        step_count = 0

        def _max_coast_chunk(s) -> float:
            """Adaptive chunk: 600s near bodies, 86400s in heliocentric."""
            sc = s.spacecraft[0]
            if sc.reference_body != CelestialBody.SUN:
                return 600.0
            return 86400.0

        while state.time.epoch < end_epoch:
            # Check if next maneuver is due
            if maneuver_idx < len(maneuvers):
                m = maneuvers[maneuver_idx]
                dt_to_burn = (m.epoch - state.time.epoch).total_seconds()

                if dt_to_burn <= 0:
                    # Execute burn with velocity-relative direction
                    sc = state.spacecraft[0]
                    direction = _resolve_direction(m.direction, sc.velocity_km_s)
                    action = AgentAction(
                        type=ActionType.BURN,
                        payload=BurnCommand(
                            direction=direction,
                            magnitude_km_s=m.magnitude_km_s,
                        ),
                    )
                    maneuver_idx += 1
                    logger.info(
                        f"BURN: {m.direction} Δv={m.magnitude_km_s*1000:.1f} m/s"
                    )
                else:
                    # Coast toward next burn, chunked adaptively
                    chunk = min(dt_to_burn, _max_coast_chunk(state))
                    action = AgentAction(
                        type=ActionType.COAST,
                        payload=CoastCommand(duration_s=chunk),
                    )
            else:
                # All burns done, coast to end
                dt_to_end = (end_epoch - state.time.epoch).total_seconds()
                chunk = min(dt_to_end, _max_coast_chunk(state))
                if chunk <= 0:
                    break
                action = AgentAction(
                    type=ActionType.COAST,
                    payload=CoastCommand(duration_s=chunk),
                )

            state, obs = step(state, action, mission, phase)
            mission = obs.mission
            phase = obs.phase
            step_count += 1

            await _broadcast_state(state)
            await asyncio.sleep(tick_interval)

            if step_count % 100 == 0:
                sc = state.spacecraft[0]
                logger.info(
                    f"Plan step {step_count} | "
                    f"T+{state.time.elapsed_s/86400:.1f}d | "
                    f"Ref: {sc.reference_body.name} | "
                    f"Fuel: {sc.fuel_kg:.3f} kg"
                )

        logger.info(f"Plan execution complete ({step_count} steps)")
        for v in viewers:
            try:
                await v.send(json.dumps({"type": "plan_complete"}))
            except Exception:
                pass

    async def tick_loop():
        nonlocal state, mission, phase, latest_obs_json
        import time as _time

        logger.info(
            f"Sim tick loop started at {tick_hz} Hz, "
            f"time warp {time_warp}x (1 real sec = {time_warp} sim sec)"
        )
        last_wall = _time.monotonic()

        while True:
            await asyncio.sleep(tick_interval)

            # Check for plan to execute
            if not plan_queue.empty():
                try:
                    plan = plan_queue.get_nowait()
                    await _execute_plan(plan)
                    last_wall = _time.monotonic()
                    continue
                except asyncio.QueueEmpty:
                    pass

            # Measure real elapsed time → sim time
            now_wall = _time.monotonic()
            real_dt = now_wall - last_wall
            last_wall = now_wall
            sim_dt = real_dt * time_warp

            # Drain queue — use latest agent action, or default coast
            action = None
            while not action_queue.empty():
                try:
                    action = action_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

            if action is None:
                action = AgentAction(
                    type=ActionType.COAST,
                    payload=CoastCommand(duration_s=sim_dt),
                )

            state, obs = step(state, action, mission, phase)
            mission = obs.mission
            phase = obs.phase

            # Broadcast UniverseState to viewers
            await _broadcast_state(state)

            # Send Observation to agents (richer: includes mission/phase)
            obs_msg = observation_to_json(obs)
            latest_obs_json = obs_msg
            if agents:
                await asyncio.gather(
                    *(a.send(obs_msg) for a in agents),
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
    parser.add_argument("--tick-hz", type=float, default=10.0)
    parser.add_argument(
        "--time-warp", type=float, default=1.0,
        help="Sim-to-real time ratio. 1=real-time, 100=1s real → 100s sim (default: 1)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run_server(port=args.port, tick_hz=args.tick_hz, time_warp=args.time_warp))
