"""Example agent client — connects to the sim server over WebSocket.

Usage:
    python -m sim.agent_client [--ws ws://localhost:8765]

Demonstrates the perception → decision → action feedback loop.
This simple agent just coasts, but logs observations to show the protocol.
Replace the `decide()` function with LLM calls for real agent behavior.
"""

from __future__ import annotations

import asyncio
import json
import logging

logger = logging.getLogger(__name__)


def decide(obs: dict) -> dict | None:
    """Given an observation, return an action dict (or None to coast).

    Replace this with LLM-based reasoning for a real agent.
    """
    sc = obs.get("spacecraft")
    if not sc:
        return None

    fuel_kg = sc.get("fuel_kg", 0)
    altitude_km = sc.get("orbit", {}).get("altitude_km", 0)
    step_num = obs.get("time", {}).get("step", 0)

    # Example: do a small prograde burn at step 50 if we have fuel
    if step_num == 50 and fuel_kg > 0.1:
        logger.info("Executing prograde burn at step 50!")
        return {
            "type": "burn",
            "payload": {
                "direction": [0.0, 1.0, 0.0],  # prograde (approx)
                "magnitude_km_s": 0.001,  # 1 m/s
            },
        }

    # Default: coast 90s
    return {
        "type": "coast",
        "payload": {"duration_s": 90.0},
    }


async def run_agent(ws_url: str = "ws://localhost:8765"):
    """Connect to sim server as an agent and run the feedback loop."""
    try:
        import websockets
    except ImportError:
        logger.error("websockets not installed. Run: uv pip install websockets")
        return

    logger.info(f"Connecting to {ws_url}")

    async for ws in websockets.connect(ws_url):
        try:
            # First message is UniverseState (viewer format) — discard it
            _ = await ws.recv()

            # Handshake: identify as agent
            await ws.send(json.dumps({"role": "agent"}))
            logger.info("Connected as agent, waiting for observations...")

            async for raw in ws:
                obs = json.loads(raw)
                time_info = obs.get("time", {})
                sc = obs.get("spacecraft", {})
                if isinstance(sc, list):
                    # Got a UniverseState instead of Observation — skip
                    continue

                # Log observation summary
                step_num = time_info.get("step", "?")
                elapsed = time_info.get("elapsed_s", 0)
                alt = sc.get("orbit", {}).get("altitude_km", 0)
                fuel = sc.get("fuel_kg", 0)
                status = sc.get("status", "?")

                logger.info(
                    f"Step {step_num} | "
                    f"T+{elapsed:.0f}s | "
                    f"Alt: {alt:.1f} km | "
                    f"Fuel: {fuel:.3f} kg | "
                    f"Status: {status}"
                )

                # Decide next action
                action = decide(obs)
                if action:
                    await ws.send(json.dumps(action))

        except Exception as e:
            logger.warning(f"Connection lost: {e}, reconnecting in 2s...")
            await asyncio.sleep(2)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Example Sim Agent Client")
    parser.add_argument("--ws", default="ws://localhost:8765")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    asyncio.run(run_agent(ws_url=args.ws))
