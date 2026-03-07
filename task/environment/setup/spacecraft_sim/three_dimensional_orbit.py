"""ThreeDimensionalOrbit — extracted from SpacecraftSimulator/tools/ThreeDimensionalOrbit.py

3D orbital element conversions: state vectors <-> orbital elements, frame transforms.
Plotting and PIL texture loading removed for headless use.
"""

import numpy as np

from spacecraft_sim.astronomical_data import AstronomicalData, CelestialBody
from spacecraft_sim.orbital_elements import OrbitalElements
from spacecraft_sim.common import wrap_to_2pi


class ThreeDimensionalOrbit:
    """Manages the conversions among different orbit representations"""

    mu = AstronomicalData.gravitational_parameter(CelestialBody.EARTH)
    J_2 = AstronomicalData.second_zonal_harmonics(CelestialBody.EARTH)
    R_E = AstronomicalData.equatiorial_radius(CelestialBody.EARTH)
    omega = AstronomicalData.ground_track_angular_velocity(CelestialBody.EARTH)

    @classmethod
    def set_celestial_body(cls, celestialBody: CelestialBody) -> None:
        cls.mu = AstronomicalData.gravitational_parameter(celestialBody)
        cls.J_2 = AstronomicalData.second_zonal_harmonics(celestialBody)
        cls.R_E = AstronomicalData.equatiorial_radius(celestialBody)
        cls.omega = AstronomicalData.ground_track_angular_velocity(celestialBody)

    # --- Algorithm 4.1: RA and Dec ---

    @classmethod
    def calculate_ra_dec(cls, r: np.ndarray) -> list:
        r_m = np.linalg.norm(r)
        l = r[0] / r_m
        m = r[1] / r_m
        n = r[2] / r_m
        delta = np.arcsin(n)
        alpha = np.arccos(l / np.cos(delta)) if m > 0 else (2 * np.pi - np.arccos(l / np.cos(delta)))
        return [alpha, delta]

    # --- Algorithm 4.2: Orbital elements from state vector ---

    @classmethod
    def calculate_orbital_elements(cls, r: np.ndarray, v: np.ndarray, deg: bool = False) -> OrbitalElements:
        oe = OrbitalElements()
        r_m = np.linalg.norm(r)
        v_m = np.linalg.norm(v)
        v_r = np.dot(r, v) / r_m

        h = np.cross(r, v)
        oe.h = np.linalg.norm(h)
        oe.a = -0.5 * cls.mu / (0.5 * v_m ** 2 - cls.mu / r_m)
        oe.i = np.arccos(h[2] / oe.h)

        # Line of nodes
        N = np.array([1, 0, 0])
        if oe.i <= 0.5 * np.pi:
            if oe.i > np.deg2rad(1) or (oe.i < np.deg2rad(1) and oe.i > 1e-6):
                N = np.cross(np.array([0, 0, 1]), h)
            else:
                N = np.array([1, 0, 0])
        else:
            if oe.i < (np.pi - np.deg2rad(1)) or (oe.i > (np.pi - np.deg2rad(1)) and (np.pi - oe.i) > 1e-6):
                N = np.cross(np.array([0, 0, 1]), h)
            else:
                N = np.array([1, 0, 0])

        N_m = np.linalg.norm(N)
        oe.Omega = np.arccos(N[0] / N_m) if N[1] >= 0 else (2 * np.pi - np.arccos(N[0] / N_m))

        e = 1 / cls.mu * ((v_m ** 2 - cls.mu / r_m) * r - r_m * v_r * v)
        oe.e = np.linalg.norm(e)

        oe.omega = (
            np.arccos(np.dot(N, e) / (N_m * oe.e))
            if e[2] >= 0
            else (2 * np.pi - np.arccos(np.dot(N, e) / (N_m * oe.e)))
        )

        oe.theta = (
            np.arccos(np.dot(e, r) / (oe.e * r_m))
            if v_r >= 0
            else (2 * np.pi - np.arccos(np.dot(e, r) / (oe.e * r_m)))
        )

        if deg:
            oe.i = np.rad2deg(oe.i)
            oe.Omega = np.rad2deg(oe.Omega)
            oe.omega = np.rad2deg(oe.omega)
            oe.theta = np.rad2deg(oe.theta)

        return oe

    # --- GEF to Perifocal ---

    @classmethod
    def gef_2_pf(cls, r: np.ndarray, v: np.ndarray) -> list:
        oe = cls.calculate_orbital_elements(r, v)
        R = cls._rotation_matrix(oe)
        return [np.matmul(R, r), np.matmul(R, v)]

    # --- Algorithm 4.5: Perifocal to GEF ---

    @classmethod
    def pf_2_gef(cls, oe: OrbitalElements) -> list:
        p = (oe.a * (1 - oe.e ** 2)) if oe.h == 0 else (oe.h ** 2 / cls.mu)
        r = p / (1 + oe.e * np.cos(oe.theta)) * np.array([np.cos(oe.theta), np.sin(oe.theta), 0])
        v = np.sqrt(cls.mu / p) * np.array([-np.sin(oe.theta), oe.e + np.cos(oe.theta), 0])
        R = cls._rotation_matrix(oe)
        return [np.matmul(R.T, r), np.matmul(R.T, v)]

    @classmethod
    def _rotation_matrix(cls, oe: OrbitalElements) -> np.ndarray:
        R_3_O = np.array([
            [+np.cos(oe.Omega), +np.sin(oe.Omega), 0],
            [-np.sin(oe.Omega), +np.cos(oe.Omega), 0],
            [0, 0, 1],
        ])
        R_1_i = np.array([
            [1, 0, 0],
            [0, +np.cos(oe.i), +np.sin(oe.i)],
            [0, -np.sin(oe.i), +np.cos(oe.i)],
        ])
        R_3_o = np.array([
            [+np.cos(oe.omega), +np.sin(oe.omega), 0],
            [-np.sin(oe.omega), +np.cos(oe.omega), 0],
            [0, 0, 1],
        ])
        return np.matmul(R_3_o, np.matmul(R_1_i, R_3_O))
