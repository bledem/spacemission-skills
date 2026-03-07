"""OrbitDetermination — extracted from SpacecraftSimulator/tools/OrbitDetermination.py

Lambert problem solver, Julian day calculations, coordinate transforms.
Plotting removed for headless use.
"""

import numpy as np
from enum import IntEnum
from datetime import datetime
from scipy.optimize import newton

from spacecraft_sim.astronomical_data import AstronomicalData, CelestialBody
from spacecraft_sim.orbital_elements import OrbitalElements
from spacecraft_sim.lagrange_coefficients import LagrangeCoefficients
from spacecraft_sim.three_dimensional_orbit import ThreeDimensionalOrbit


class OrbitDirection(IntEnum):
    PROGRADE = 0
    RETROGRADE = 1


class OrbitDetermination:
    """Orbit determination algorithms: Lambert solver, Julian day, coordinate transforms"""

    mu = AstronomicalData.gravitational_parameter(CelestialBody.EARTH)

    @classmethod
    def set_celestial_body(cls, celestialBody: CelestialBody) -> None:
        cls.mu = AstronomicalData.gravitational_parameter(celestialBody)

    # --- Lambert equation ---

    @classmethod
    def lambert_equation(cls, z: float, r_1: float, r_2: float, A: float, dt: float) -> float:
        y = r_1 + r_2 + A * (z * LagrangeCoefficients.S(z) - 1) / np.sqrt(LagrangeCoefficients.C(z))
        return (y / LagrangeCoefficients.C(z)) ** (3 / 2) * LagrangeCoefficients.S(z) + A * np.sqrt(y) - np.sqrt(cls.mu) * dt

    @classmethod
    def lambert_equation_first_derivative(cls, z: float, r_1: float, r_2: float, A: float, dt: float) -> float:
        S = LagrangeCoefficients.S(z)
        C = LagrangeCoefficients.C(z)
        y0 = r_1 + r_2 + A * (0 * LagrangeCoefficients.S(0) - 1) / np.sqrt(LagrangeCoefficients.C(0))
        y = r_1 + r_2 + A * (z * S - 1) / np.sqrt(C)
        if z == 0:
            return np.sqrt(2) / 40 * y0 ** (3 / 2) + A / 8 * (np.sqrt(y0) + A * 1 / np.sqrt(2 * y0))
        else:
            return (
                (y / C) ** (3 / 2) * (1 / (2 * z) * (C - 3 / 2 * S / C) + 3 / 4 * S ** 2 / C)
                + A / 8 * (3 * S / C * np.sqrt(y) + A * np.sqrt(C / y))
            )

    # --- Algorithm 5.2: Lambert problem ---

    @classmethod
    def solve_lambert_problem(cls, r_1: np.ndarray, r_2: np.ndarray, dt: float,
                              direction: OrbitDirection = OrbitDirection.PROGRADE) -> list:
        """Returns [v_1, v_2, orbital_elements, theta_2]"""
        r_1_m = np.linalg.norm(r_1)
        r_2_m = np.linalg.norm(r_2)

        temp = np.arccos(np.dot(r_1, r_2) / (r_1_m * r_2_m))
        cond = np.cross(r_1, r_2)[2]

        if direction == OrbitDirection.PROGRADE:
            dtheta = temp if cond >= 0 else (2 * np.pi - temp)
        else:
            dtheta = temp if cond < 0 else (2 * np.pi - temp)

        A = np.sin(dtheta) * np.sqrt((r_1_m * r_2_m) / (1 - np.cos(dtheta)))

        z0 = -4
        while cls.lambert_equation(z0, r_1_m, r_2_m, A, dt) < 0:
            z0 = z0 + 0.1

        try:
            z = newton(cls.lambert_equation, 1.5, cls.lambert_equation_first_derivative,
                       args=(r_1_m, r_2_m, A, dt))
        except Exception:
            return [np.zeros(r_1.shape), np.zeros(r_2.shape), OrbitalElements(), 0.0]

        y = r_1_m + r_2_m + A * (z * LagrangeCoefficients.S(z) - 1) / np.sqrt(LagrangeCoefficients.C(z))

        f = 1 - y / r_1_m
        g = A * np.sqrt(y / cls.mu)
        dg_dt = 1 - y / r_2_m

        v_1 = 1 / g * (r_2 - f * r_1)
        v_2 = 1 / g * (dg_dt * r_2 - r_1)

        ThreeDimensionalOrbit.mu = cls.mu
        return [v_1, v_2, ThreeDimensionalOrbit.calculate_orbital_elements(r_1, v_1),
                ThreeDimensionalOrbit.calculate_orbital_elements(r_2, v_2).theta]

    # --- Julian day ---

    @classmethod
    def julian_day(cls, year: int, month: int, day: int, hours: float, minutes: float, seconds: float) -> float:
        J_0 = (
            367 * year
            - int(7 * (year + int((month + 9) / 12)) / 4)
            + int(275 * month / 9)
            + day + 1_721_013.5
        )
        UT = hours + minutes / 60 + seconds / 3600
        return J_0 + UT / 24

    @classmethod
    def frac_day_2_hms(cls, fracDay: float) -> list:
        hours = int(fracDay * 24)
        minutes = int((fracDay * 24 - hours) * 60)
        seconds = ((fracDay * 24 - hours) * 60 - minutes) * 60
        return [hours, minutes, seconds]

    @classmethod
    def julian_day_2_date(cls, JD: float) -> datetime:
        z = int(JD + 0.5)
        f = JD + 0.5 - z
        if z < 2_299_161:
            A = z
        else:
            alpha = int((z - 1_867_216.25) / 36_524.25)
            A = z + 1 + alpha - int(alpha / 4)
        B = A + 1524
        C = int((B - 122.1) / 365.25)
        D = int(365.25 * C)
        E = int((B - D) / 30.6001)
        day = B - D - int(30.6001 * E) + f
        month = E - 1 if E < 14 else E - 13
        year = C - 4716 if month > 2 else C - 4715
        h, m, s = cls.frac_day_2_hms(day - int(day))
        return datetime(int(year), int(month), int(day), h, m, int(s))
