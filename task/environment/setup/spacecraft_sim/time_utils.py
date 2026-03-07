"""Time utilities — extracted from SpacecraftSimulator/tools/Time.py

Algorithms to evaluate time on orbits (circular, elliptical, parabolic, hyperbolic).
Plotting removed for headless use.
"""

import numpy as np
from enum import IntEnum
from scipy.optimize import newton

from spacecraft_sim.astronomical_data import AstronomicalData, CelestialBody


class DirectionType(IntEnum):
    MEAN_ANOMALY_TO_TIME = 0
    TIME_TO_MEAN_ANOMALY = 1


class Time:
    """Manages all the algorithms to link position to time on an orbit"""

    mu = AstronomicalData.gravitational_parameter(CelestialBody.EARTH)

    @classmethod
    def set_celestial_body(cls, celestialBody: CelestialBody) -> None:
        cls.mu = AstronomicalData.gravitational_parameter(celestialBody)

    # --- Circular orbit (Section 3.3) ---

    @classmethod
    def calculate_circular_orbit(cls, direction: DirectionType, T: float, **kwargs) -> float:
        if direction == DirectionType.MEAN_ANOMALY_TO_TIME:
            theta = kwargs['theta']
            return theta / (2 * np.pi) * T
        else:
            t = kwargs['t']
            return (2 * np.pi) / T * t

    # --- Elliptical orbit (Algorithm 3.1) ---

    @classmethod
    def calculate_elliptical_orbit(cls, direction: DirectionType, T: float, e: float, **kwargs) -> float:
        if direction == DirectionType.MEAN_ANOMALY_TO_TIME:
            theta = kwargs['theta']
            E = 2 * np.arctan(np.sqrt((1 - e) / (1 + e)) * np.tan(theta / 2))
            M_e = E - e * np.sin(E)
            return M_e / (2 * np.pi) * T
        else:
            t = kwargs['t']
            M_e = (2 * np.pi) / T * t
            f = lambda E, e, M_e: E - e * np.sin(E) - M_e
            df = lambda E, e, M_e: 1 - e * np.cos(E)
            E0 = (M_e + 0.5 * e) if M_e < np.pi else (M_e - 0.5 * e)
            E = newton(f, E0, df, args=(e, M_e))
            theta = 2 * np.arctan(np.sqrt((1 + e) / (1 - e)) * np.tan(E / 2))
            return theta if theta > 0 else (theta + 2 * np.pi)

    # --- Parabolic orbit (Section 3.5) ---

    @classmethod
    def calculate_parabolic_orbit(cls, direction: DirectionType, h: float, **kwargs) -> float:
        if direction == DirectionType.MEAN_ANOMALY_TO_TIME:
            theta = kwargs['theta']
            M_p = 1 / 2 * np.tan(theta / 2) + 1 / 6 * np.tan(theta / 2) ** 3
            return M_p * h ** 3 / cls.mu ** 2
        else:
            t = kwargs['t']
            M_p = cls.mu ** 2 / h ** 3 * t
            return 2 * np.arctan(
                (3 * M_p + np.sqrt((3 * M_p) ** 2 + 1)) ** (1 / 3)
                - (3 * M_p + np.sqrt((3 * M_p) ** 2 + 1)) ** (-1 / 3)
            )

    # --- Hyperbolic orbit (Algorithm 3.2) ---

    @classmethod
    def calculate_hyperbolic_orbit(cls, direction: DirectionType, h: float, e: float, **kwargs) -> float:
        if direction == DirectionType.MEAN_ANOMALY_TO_TIME:
            theta = kwargs['theta']
            F = 2 * np.arctanh(np.sqrt((e - 1) / (e + 1)) * np.tan(theta / 2))
            M_h = e * np.sinh(F) - F
            return M_h * h ** 3 / cls.mu ** 2 * (e ** 2 - 1) ** (-3 / 2)
        else:
            t = kwargs['t']
            M_h = cls.mu ** 2 / h ** 3 * (e ** 2 - 1) ** (3 / 2) * t
            f = lambda F, e, M_h: e * np.sinh(F) - F - M_h
            df = lambda F, e, M_h: e * np.cosh(F) - 1
            F = newton(f, 3.45, df, args=(e, M_h))
            theta = 2 * np.arctan(np.sqrt((e + 1) / (e - 1)) * np.tanh(F / 2))
            return theta if theta > 0 else (theta + 2 * np.pi)
