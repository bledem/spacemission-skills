"""OrbitalManeuvers — extracted from SpacecraftSimulator/tools/OrbitalManeuvers.py

Hohmann transfers, bi-elliptic transfers, propellant mass (Tsiolkovsky), and more.
"""

import numpy as np

from spacecraft_sim.astronomical_data import AstronomicalData, CelestialBody
from spacecraft_sim.orbital_elements import OrbitalElements
from spacecraft_sim.maneuver_result import ManeuverResult, HohmannDirection
from spacecraft_sim.time_utils import Time, DirectionType
from spacecraft_sim.orbit_determination import OrbitDetermination
from spacecraft_sim.two_body_problem import TwoBodyProblem
from spacecraft_sim.lagrange_coefficients import LagrangeCoefficients
from spacecraft_sim.three_dimensional_orbit import ThreeDimensionalOrbit


class OrbitalManeuvers:
    """Implements different maneuvers and the related algorithms"""

    mu = AstronomicalData.gravitational_parameter(CelestialBody.EARTH)
    g_0 = AstronomicalData.gravity(CelestialBody.EARTH, km=True)
    I_sp = 300.0  # Specific Impulse [s]

    @classmethod
    def set_celestial_body(cls, celestialBody: CelestialBody) -> None:
        cls.mu = AstronomicalData.gravitational_parameter(celestialBody)
        cls.g_0 = AstronomicalData.gravity(celestialBody, km=True)

    @classmethod
    def set_specific_impulse(cls, I_sp: float) -> None:
        cls.I_sp = I_sp

    @classmethod
    def propellant_mass(cls, m: float, dv: float) -> float:
        """Ideal rocket equation (Tsiolkovsky) mass calculation"""
        return m * (1 - np.exp(-dv / (cls.I_sp * cls.g_0)))

    @classmethod
    def hohmann_transfer(cls, r_p_1: float, r_a_1: float, r_p_2: float, r_a_2: float,
                         direction: HohmannDirection = HohmannDirection.PER2APO,
                         m: float = 0.0) -> ManeuverResult:
        """Hohmann transfer maneuver"""
        result = ManeuverResult()

        h_1 = np.sqrt(2 * cls.mu) * np.sqrt(r_a_1 * r_p_1 / (r_a_1 + r_p_1))
        v_p_1 = h_1 / r_p_1
        v_a_1 = h_1 / r_a_1

        h_2 = np.sqrt(2 * cls.mu) * np.sqrt(r_a_2 * r_p_2 / (r_a_2 + r_p_2))
        v_p_2 = h_2 / r_p_2
        v_a_2 = h_2 / r_a_2

        a_T = e_T = h_T = v_p_T = v_a_T = 0.0

        if direction == HohmannDirection.PER2APO:
            a_T = 0.5 * (r_p_1 + r_a_2)
            e_T = (r_a_2 - r_p_1) / (r_a_2 + r_p_1)
            h_T = np.sqrt(2 * cls.mu) * np.sqrt(r_a_2 * r_p_1 / (r_a_2 + r_p_1))
            v_p_T = h_T / r_p_1
            v_a_T = h_T / r_a_2
        elif direction == HohmannDirection.APO2PER:
            a_T = 0.5 * (r_p_2 + r_a_1)
            e_T = (r_a_1 - r_p_2) / (r_a_1 + r_p_2)
            h_T = np.sqrt(2 * cls.mu) * np.sqrt(r_a_1 * r_p_2 / (r_a_1 + r_p_2))
            v_p_T = h_T / r_p_2
            v_a_T = h_T / r_a_1

        T_T = 2 * np.pi / float(np.sqrt(cls.mu)) * a_T ** (3 / 2)

        dv_1 = dv_2 = 0.0
        if direction == HohmannDirection.PER2APO:
            dv_1 = abs(v_p_T - v_p_1)
            dv_2 = abs(v_a_2 - v_a_T)
        elif direction == HohmannDirection.APO2PER:
            dv_1 = abs(v_a_T - v_a_1)
            dv_2 = abs(v_p_2 - v_p_T)

        result.dv = dv_1 + dv_2
        result.dt = 0.5 * T_T
        dm_1 = cls.propellant_mass(m, dv_1)
        dm_2 = cls.propellant_mass(m - dm_1, dv_2)
        result.dm = dm_1 + dm_2
        result.oe = OrbitalElements(h_T, e_T, 0, 0, 0, 0, a_T)
        return result

    @classmethod
    def bi_elliptic_hohmann_transfer(cls, r_p_1: float, r_a_1: float, r_p_2: float, r_a_2: float,
                                     r_3: float, direction: HohmannDirection = HohmannDirection.PER2APO,
                                     m: float = 0.0) -> list:
        """Bi-Elliptic Hohmann transfer maneuver"""
        if direction == HohmannDirection.PER2APO:
            hohmann_1 = cls.hohmann_transfer(r_p_1, r_a_1, r_p_1, r_3, HohmannDirection.PER2APO, m)
            hohmann_2 = cls.hohmann_transfer(r_p_1, r_3, r_p_2, r_a_2, HohmannDirection.APO2PER, m - hohmann_1.dm)
            return [hohmann_1, hohmann_2]
        return []
