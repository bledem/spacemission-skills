"""Lagrange Coefficients — extracted from SpacecraftSimulator/tools/LagrangeCoefficients.py

Orbit propagation via universal variable formulation.
"""

import numpy as np
from scipy.optimize import newton

from spacecraft_sim.astronomical_data import AstronomicalData, CelestialBody


class LagrangeCoefficients:
    """Manages all the algorithms based on the Lagrange coefficients"""

    mu = AstronomicalData.gravitational_parameter(CelestialBody.EARTH)

    # --- Algorithm 2.3: Position/velocity by angle ---

    @classmethod
    def calculate_position_velocity_by_angle(cls, r_0: np.ndarray, v_0: np.ndarray, dtheta: float) -> list:
        r_0_m = np.linalg.norm(r_0)
        v_0_m = np.linalg.norm(v_0)
        v_r0 = np.dot(r_0, v_0) / r_0_m
        h = r_0_m * np.sqrt(v_0_m ** 2 - v_r0 ** 2)

        r = h ** 2 / cls.mu * 1 / (
            1 + (h ** 2 / (cls.mu * r_0_m) - 1) * np.cos(dtheta)
            - h * v_r0 / cls.mu * np.sin(dtheta)
        )

        f = 1 - cls.mu * r / h ** 2 * (1 - np.cos(dtheta))
        g = r * r_0_m / h * np.sin(dtheta)
        df_dt = (
            cls.mu / h * (1 - np.cos(dtheta)) / np.sin(dtheta)
            * (cls.mu / h ** 2 * (1 - np.cos(dtheta)) - 1 / r_0_m - 1 / r)
        )
        dg_dt = 1 - cls.mu * r_0_m / h ** 2 * (1 - np.cos(dtheta))

        return [f * r_0 + g * v_0, df_dt * r_0 + dg_dt * v_0]

    # --- Stumpff functions ---

    @classmethod
    def S(cls, z: float) -> float:
        if z > 0:
            return (np.sqrt(z) - np.sin(np.sqrt(z))) / np.sqrt(z) ** 3
        elif z < 0:
            return (np.sinh(np.sqrt(-z)) - np.sqrt(-z)) / np.sqrt(-z) ** 3
        else:
            return 1 / 6

    @classmethod
    def C(cls, z: float) -> float:
        if z > 0:
            return (1 - np.cos(np.sqrt(z))) / z
        elif z < 0:
            return (np.cosh(np.sqrt(-z)) - 1) / (-z)
        else:
            return 1 / 2

    # --- Algorithm 3.3: Universal variable ---

    @classmethod
    def calculate_universal_variable(cls, r_0: float, v_r0: float, alpha: float, dt: float) -> float:
        f = lambda chi, r0, vr0, a, dt: (
            r0 * vr0 / np.sqrt(cls.mu) * chi ** 2 * cls.C(a * chi ** 2)
            + (1 - a * r0) * chi ** 3 * cls.S(a * chi ** 2)
            + r0 * chi - np.sqrt(cls.mu) * dt
        )
        df = lambda chi, r0, vr0, a, dt: (
            r0 * vr0 / np.sqrt(cls.mu) * chi * (1 - a * chi ** 2 * cls.S(a * chi ** 2))
            + (1 - a * r0) * chi ** 2 * cls.C(a * chi ** 2) + r0
        )
        chi_0 = np.sqrt(cls.mu) * np.abs(alpha) * dt
        return newton(f, chi_0, df, args=(r_0, v_r0, alpha, dt))

    @classmethod
    def calculate_lagrange_coefficients(cls, r_0: float, alpha: float, dt: float, chi: float) -> list:
        f = 1 - chi ** 2 / r_0 * cls.C(alpha * chi ** 2)
        g = dt - 1 / np.sqrt(cls.mu) * chi ** 3 * cls.S(alpha * chi ** 2)
        return [f, g]

    # --- Algorithm 3.4: Position/velocity by time ---

    @classmethod
    def calculate_position_velocity_by_time(cls, r_0: np.ndarray, v_0: np.ndarray, dt: float) -> list:
        r_0_m = np.linalg.norm(r_0)
        v_0_m = np.linalg.norm(v_0)
        v_r0 = np.dot(r_0, v_0) / r_0_m
        alpha = 2 / r_0_m - v_0_m ** 2 / cls.mu

        chi = cls.calculate_universal_variable(r_0_m, v_r0, alpha, dt)
        z = alpha * chi ** 2

        f = 1 - chi ** 2 / r_0_m * cls.C(z)
        g = dt - 1 / np.sqrt(cls.mu) * chi ** 3 * cls.S(z)
        r = f * r_0 + g * v_0

        df_dt = np.sqrt(cls.mu) / (np.linalg.norm(r) * r_0_m) * (alpha * chi ** 3 * cls.S(z) - chi)
        dg_dt = 1 - chi ** 2 / np.linalg.norm(r) * cls.C(z)
        v = df_dt * r_0 + dg_dt * v_0

        return [r, v]
