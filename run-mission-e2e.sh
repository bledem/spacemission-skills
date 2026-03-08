#!/bin/bash
#
# Run the Deep Space Explorer mission e2e.
#
# This script:
# 1. Sets up the spacecraft_sim Python package
# 2. Runs the mission solver to generate a mission plan
# 3. Verifies the mission plan
#
# Usage: ./run-mission-e2e.sh [--sample]
#   --sample  Use sample mission instead of generating new one

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$SCRIPT_DIR/task"
MISSION_OUTPUT="/tmp/mission_plan.json"

# Parse args
USE_SAMPLE=false
for arg in "$@"; do
    case $arg in
        --sample) USE_SAMPLE=true ;;
    esac
done

echo "=== Deep Space Explorer E2E ==="
echo ""

# Step 1: Setup Python environment
echo "[1/3] Setting up Python environment..."
cd "$TASK_DIR/environment/setup"

# Create venv if it doesn't exist
if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install spacecraft_sim if needed
if ! python3 -c "import spacecraft_sim" 2>/dev/null; then
    pip install -e . -q
fi

# Step 2: Generate mission plan
echo "[2/3] Generating mission plan..."

if $USE_SAMPLE; then
    echo "  Using sample mission (Mars Hohmann Round-Trip)..."
    # Create a valid sample mission
    python3 -c "
import json

plan = {
    'mission_name': 'Mars Hohmann Round-Trip',
    'departure_date': '2026-05-01',
    'total_delta_v_km_s': 11.4,
    'max_distance_AU': 1.52,
    'mission_duration_days': 970,
    'tier': 'Bronze',
    'verification': {
        'mission_duration_days': 970,
        'delta_v_breakdown_km_s': {
            'earth_departure': 3.6,
            'mars_arrival': 2.1,
            'mars_departure': 2.1,
            'earth_arrival': 3.6
        }
    },
    'phases': [
        {
            'phase': 'earth_departure',
            'date': '2026-05-01',
            'delta_v_km_s': 3.6,
            'orbit': {
                'a_AU': 1.26,
                'e': 0.208,
                'omega_rad': 0,
                'period_days': 516
            },
            'description': 'Trans-Mars injection burn'
        },
        {
            'phase': 'return_departure',
            'date': '2027-04-01',
            'delta_v_km_s': 2.1,
            'orbit': {
                'a_AU': 1.26,
                'e': 0.208,
                'omega_rad': 3.14159,
                'period_days': 516
            },
            'description': 'Mars departure burn'
        },
        {
            'phase': 'earth_arrival',
            'date': '2028-12-01',
            'delta_v_km_s': 3.6,
            'orbit': None,
            'description': 'Earth capture burn'
        }
    ],
    'flybys': []
}

with open('$MISSION_OUTPUT', 'w') as f:
    json.dump(plan, f, indent=2)
"
else
    echo "  Running Lambert solver for optimal transfer..."
    # Run the actual solver
    python3 -c "
import sys
sys.path.insert(0, '../environment/setup')

import json
import os
import warnings
import numpy as np

warnings.filterwarnings('ignore', category=RuntimeWarning)
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
    v_p = np.sqrt(v_inf ** 2 + 2 * mu_earth / r_p)
    v_c = np.sqrt(mu_earth / r_p)
    return abs(v_p - v_c)


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

# Format for visualizer
plan = {
    'mission_name': 'Lambert Mars Round Trip',
    'departure_date': dep_date.strftime('%Y-%m-%d'),
    'total_delta_v_km_s': round(total_dv, 4),
    'max_distance_AU': round(r_apo, 4),
    'mission_duration_days': duration,
    'tier': 'Bronze' if r_apo < 2 else 'Silver',
    'verification': {
        'mission_duration_days': duration,
        'delta_v_breakdown_km_s': {
            'earth_departure': round(dv_dep, 4),
            'mars_arrival': 0,
            'mars_departure': round(dv_mars_esc, 4),
            'earth_arrival': round(dv_earth_cap, 4)
        }
    },
    'phases': [
        {
            'phase': 'earth_departure',
            'date': dep_date.strftime('%Y-%m-%d'),
            'delta_v_km_s': round(dv_dep, 4),
            'orbit': {
                'a_AU': round(float(oe_out.a) / AU_KM, 4),
                'e': round(float(oe_out.e), 6),
                'omega_rad': 0,
                'period_days': round(2 * 3.14159 * np.sqrt(float(oe_out.a)**3 / 1.327e11) / 86400, 0)
            },
            'description': 'Trans-Mars injection burn'
        },
        {
            'phase': 'return_departure',
            'date': ret_dep.strftime('%Y-%m-%d'),
            'delta_v_km_s': round(dv_mars_esc, 4),
            'orbit': {
                'a_AU': round(float(oe_ret.a) / AU_KM, 4),
                'e': round(float(oe_ret.e), 6),
                'omega_rad': 3.14159,
                'period_days': round(2 * 3.14159 * np.sqrt(float(oe_ret.a)**3 / 1.327e11) / 86400, 0)
            },
            'description': 'Mars departure burn'
        },
        {
            'phase': 'earth_arrival',
            'date': ret_arr.strftime('%Y-%m-%d'),
            'delta_v_km_s': round(dv_earth_cap, 4),
            'orbit': None,
            'description': 'Earth capture burn'
        }
    ],
    'flybys': []
}

output_path = '$MISSION_OUTPUT'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(plan, f, indent=2)

print(f'  Total dv: {total_dv:.3f} km/s | Distance: {r_apo:.3f} AU | Duration: {duration} days')
"
fi

echo "  Mission plan saved to $MISSION_OUTPUT"

# Step 3: Verify the mission
echo "[3/3] Verifying mission plan..."
python3 -c "
import json

with open('$MISSION_OUTPUT', 'r') as f:
    plan = json.load(f)

dist = plan.get('max_distance_AU', 0)
dv = plan.get('total_delta_v_km_s', 0)
duration = plan.get('mission_duration_days', plan.get('verification', {}).get('mission_duration_days', 0))

# Determine tier
if dist >= 6.0:
    tier = 'PLATINUM'
elif dist >= 4.0:
    tier = 'GOLD'
elif dist >= 2.0:
    tier = 'SILVER'
elif dist >= 1.5:
    tier = 'BRONZE'
else:
    tier = 'SUB-BRONZE'

print(f'  Mission: {plan.get(\"mission_name\")}')
print(f'  Tier: {tier}')
print(f'  Max Distance: {dist:.3f} AU')
print(f'  Total Delta-V: {dv:.3f} km/s')
print(f'  Duration: {duration} days')

valid = dv <= 12.0 and duration <= 7305
if valid:
    print('  Status: VALID')
else:
    print('  Status: WARNING - constraints may be violated')
"

echo ""
echo "=== E2E complete ==="
echo "Mission plan: $MISSION_OUTPUT"
