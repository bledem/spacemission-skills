"""
spacecraft_sim — Extracted orbital mechanics engine from SpacecraftSimulator.

Provides deterministic, GUI-free computation of:
- Planetary ephemeris (Algorithm 8.1, Curtis)
- Lambert problem solver (Algorithm 5.2, Curtis)
- Interplanetary trajectory design (departure, arrival, flyby, optimal transfer)
- Orbital maneuvers (Hohmann, bi-elliptic, plane change, etc.)
- Orbit propagation via Lagrange coefficients
- Two-body problem orbital parameters
- 3D orbital element conversions

Original source: SpacecraftSimulator by Alessio Negri (LGPL v3)
Reference: "Orbital Mechanics for Engineering Students" — Howard D. Curtis
"""

from spacecraft_sim.astronomical_data import (
    AstronomicalData,
    CelestialBody,
    Planet,
    celestial_body_from_planet,
    celestial_body_from_index,
    index_from_celestial_body,
    planet_from_index,
    index_from_planet,
)
from spacecraft_sim.orbital_elements import OrbitalElements
from spacecraft_sim.orbital_parameters import OrbitalParameters
from spacecraft_sim.maneuver_result import ManeuverResult, HohmannDirection
from spacecraft_sim.time_utils import Time, DirectionType
from spacecraft_sim.lagrange_coefficients import LagrangeCoefficients
from spacecraft_sim.orbit_determination import OrbitDetermination, OrbitDirection
from spacecraft_sim.three_dimensional_orbit import ThreeDimensionalOrbit
from spacecraft_sim.two_body_problem import TwoBodyProblem
from spacecraft_sim.orbital_maneuvers import OrbitalManeuvers
from spacecraft_sim.interplanetary_trajectories import InterplanetaryTrajectories, FlybySide
from spacecraft_sim.common import wrap_to_2pi, wrap_to360deg, daterange, daterange_length

__all__ = [
    "AstronomicalData", "CelestialBody", "Planet",
    "celestial_body_from_planet", "celestial_body_from_index",
    "index_from_celestial_body", "planet_from_index", "index_from_planet",
    "OrbitalElements", "OrbitalParameters", "ManeuverResult", "HohmannDirection",
    "Time", "DirectionType",
    "LagrangeCoefficients", "OrbitDetermination", "OrbitDirection",
    "ThreeDimensionalOrbit", "TwoBodyProblem",
    "OrbitalManeuvers", "InterplanetaryTrajectories", "FlybySide",
    "wrap_to_2pi", "wrap_to360deg", "daterange", "daterange_length",
]
