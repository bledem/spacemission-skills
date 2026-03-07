#!/usr/bin/env python3
"""
Oracle solution for Deep Space Explorer task.

Produces a valid mission_plan.json to verify the task pipeline works end-to-end.
Uses a simple Earth-Mars Lambert transfer with known-good dates.
"""

import json
import os
import warnings
import numpy as np

warnings.filterwarnings("ignore", category=RuntimeWarning)
from datetime import datetime

from spacecraft_sim import (
    InterplanetaryTrajectories,
    OrbitDetermination,
    AstronomicalData,
    CelestialBody,
)

AU_KM = 149_597_870.7
PARKING_R = 6678.0
mu_earth = AstronomicalData.gravitational_parameter(CelestialBody.EARTH)


def dv_from_vinf(v_inf, r_p=PARKING_R):
    """Delta-v for parking orbit <-> hyperbola transition."""
    v_p = np.sqrt(v_inf ** 2 + 2 * mu_earth / r_p)
    v_c = np.sqrt(mu_earth / r_p)
    return abs(v_p - v_c)


def main():
    # Known-good Earth-Mars window
    dep_date = datetime(2028, 9, 15)
    mars_arr = datetime(2029, 6, 12)

    # Outbound Lambert
    R1, V1 = InterplanetaryTrajectories.ephemeris(CelestialBody.EARTH, dep_date)
    R2, V2 = InterplanetaryTrajectories.ephemeris(CelestialBody.MARS, mars_arr)
    dt_out = (mars_arr - dep_date).total_seconds()

    OrbitDetermination.set_celestial_body(CelestialBody.SUN)
    VD, VA, oe_out, _ = OrbitDetermination.solve_lambert_problem(R1, R2, dt_out)

    vinf_dep = np.linalg.norm(VD - V1)
    dv_dep = dv_from_vinf(vinf_dep)
    r_apo = oe_out.a * (1 + oe_out.e) / AU_KM

    # Return leg
    ret_dep = datetime(2030, 10, 1)
    ret_arr = datetime(2031, 5, 1)

    R3, V3 = InterplanetaryTrajectories.ephemeris(CelestialBody.MARS, ret_dep)
    R4, V4 = InterplanetaryTrajectories.ephemeris(CelestialBody.EARTH, ret_arr)
    dt_ret = (ret_arr - ret_dep).total_seconds()

    VD2, VA2, oe_ret, _ = OrbitDetermination.solve_lambert_problem(R3, R4, dt_ret)

    mu_mars = AstronomicalData.gravitational_parameter(CelestialBody.MARS)
    vinf_mars_dep = np.linalg.norm(VD2 - V3)
    r_p_mars = AstronomicalData.equatiorial_radius(CelestialBody.MARS) + 300
    v_p_mars = np.sqrt(vinf_mars_dep ** 2 + 2 * mu_mars / r_p_mars)
    v_c_mars = np.sqrt(mu_mars / r_p_mars)
    dv_mars_esc = abs(v_p_mars - v_c_mars)

    vinf_earth_arr = np.linalg.norm(VA2 - V4)
    dv_earth_cap = dv_from_vinf(vinf_earth_arr)

    total_dv = float(dv_dep + dv_mars_esc + dv_earth_cap)
    dv_dep = float(dv_dep)
    dv_mars_esc = float(dv_mars_esc)
    dv_earth_cap = float(dv_earth_cap)
    r_apo = float(r_apo)
    duration = (ret_arr - dep_date).days

    plan = {
        "mission_name": "Oracle Mars Round Trip",
        "strategy": "lambert",
        "departure_date": dep_date.strftime("%Y-%m-%d"),
        "return_date": ret_arr.strftime("%Y-%m-%d"),
        "total_delta_v_km_s": round(total_dv, 4),
        "max_distance_AU": round(r_apo, 4),
        "phases": [
            {
                "phase": "earth_departure",
                "date": dep_date.strftime("%Y-%m-%d"),
                "maneuver": "departure_burn",
                "delta_v_km_s": round(dv_dep, 4),
                "from_body": "EARTH",
                "to_body": "MARS",
                "parking_orbit_radius_km": PARKING_R,
                "transfer_orbit": {
                    "a_km": round(float(oe_out.a), 2),
                    "e": round(float(oe_out.e), 6),
                    "i_deg": round(float(np.rad2deg(oe_out.i)), 4),
                },
            },
            {
                "phase": "return_departure",
                "date": ret_dep.strftime("%Y-%m-%d"),
                "delta_v_km_s": round(dv_mars_esc, 4),
                "transfer_orbit": {
                    "a_km": round(float(oe_ret.a), 2),
                    "e": round(float(oe_ret.e), 6),
                },
            },
            {
                "phase": "earth_arrival",
                "date": ret_arr.strftime("%Y-%m-%d"),
                "delta_v_km_s": round(dv_earth_cap, 4),
                "capture_orbit": {
                    "periapsis_km": PARKING_R,
                    "period_hours": 1.5,
                },
            },
        ],
        "verification": {
            "total_delta_v_check": bool(total_dv <= 12.0),
            "mission_duration_days": duration,
            "earth_return_distance_km": 0.0,
            "all_constraints_satisfied": bool(total_dv <= 12.0 and duration <= 7305),
        },
    }

    output_path = "/app/mission_plan.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(plan, f, indent=2)

    print(f"Mission plan written to {output_path}")
    print(f"Total dv: {total_dv:.3f} km/s | Distance: {r_apo:.3f} AU | Duration: {duration} days")


if __name__ == "__main__":
    main()
