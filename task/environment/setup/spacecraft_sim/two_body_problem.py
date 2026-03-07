"""TwoBodyProblem — extracted from SpacecraftSimulator/tools/TwoBodyProblem.py

Two-body problem solver: orbital parameters, relative motion integration.
Plotting removed for headless use.
"""

import numpy as np
from scipy.integrate import solve_ivp

from spacecraft_sim.astronomical_data import AstronomicalData, CelestialBody
from spacecraft_sim.orbital_parameters import OrbitalParameters
from spacecraft_sim.time_utils import Time, DirectionType


class TwoBodyProblem:
    """Implements all the algorithms to solve the Two Body Problem"""

    g_0 = AstronomicalData.gravity(CelestialBody.EARTH, True)
    mu = AstronomicalData.gravitational_parameter(CelestialBody.EARTH)

    @classmethod
    def set_celestial_body(cls, celestialBody: CelestialBody) -> None:
        cls.g_0 = AstronomicalData.gravity(celestialBody, True)
        cls.mu = AstronomicalData.gravitational_parameter(celestialBody)

    @classmethod
    def relative_eom(cls, t: float, X: np.ndarray) -> np.ndarray:
        x, y, z, v_x, v_y, v_z = X
        r = np.sqrt(x ** 2 + y ** 2 + z ** 2)
        dX_dt = np.zeros(6)
        dX_dt[0] = v_x
        dX_dt[1] = v_y
        dX_dt[2] = v_z
        dX_dt[3] = -(cls.mu / r ** 3) * x
        dX_dt[4] = -(cls.mu / r ** 3) * y
        dX_dt[5] = -(cls.mu / r ** 3) * z
        return dX_dt

    @classmethod
    def simulate_relative_motion(cls, y_0: np.ndarray, t_0: float = 0.0, t_f: float = 0.0) -> dict:
        parameters = cls.calculate_orbital_parameters(y_0[:3], y_0[3:])
        if t_f == 0.0 and t_0 >= 0.0:
            t_f = parameters.T
        if parameters.e >= 1.0:
            t_f = Time.calculate_hyperbolic_orbit(
                DirectionType.MEAN_ANOMALY_TO_TIME, h=parameters.h, e=parameters.e,
                theta=parameters.theta_inf * 0.999
            )
        if t_f < t_0:
            raise Exception('Invalid integration time')
        result = solve_ivp(
            fun=cls.relative_eom, t_span=[t_0, t_f], y0=y_0,
            method='RK45', args=(), rtol=1e-8, atol=1e-8
        )
        if not result['success']:
            raise Exception(result['message'])
        return dict(t=result['t'], y=result['y'], dt=np.abs(result['t'][-1] - result['t'][0]))

    @classmethod
    def calculate_orbital_parameters(cls, r: np.ndarray, v: np.ndarray) -> OrbitalParameters:
        params = OrbitalParameters()
        h = np.cross(r, v)
        params.h = np.linalg.norm(h)
        params.epsilon = np.linalg.norm(v) ** 2 / 2 - cls.mu / np.linalg.norm(r)
        params.e = np.sqrt((2 * np.linalg.norm(h) ** 2 * params.epsilon) / (cls.mu ** 2) + 1)

        if params.e == 0:  # Circular
            params.r_p = np.linalg.norm(r)
            params.r_a = np.linalg.norm(r)
            params.a = np.linalg.norm(r)
            params.b = np.linalg.norm(r)
            params.T = (2 * np.pi) / np.sqrt(cls.mu) * np.linalg.norm(r) ** (3 / 2)
        elif 0 < params.e < 1:  # Elliptical
            params.r_p = params.h ** 2 / cls.mu * 1 / (1 + params.e)
            params.r_a = params.h ** 2 / cls.mu * 1 / (1 - params.e)
            params.a = (params.r_p + params.r_a) / 2
            params.b = params.a * np.sqrt(1 - params.e ** 2)
            params.T = (2 * np.pi) / np.sqrt(cls.mu) * params.a ** (3 / 2)
        elif params.e == 1:  # Parabolic
            params.r_p = params.h ** 2 / cls.mu * 1 / 2
            params.r_a = np.inf
            params.a = np.inf
            params.b = 0
            params.T = np.inf
            params.v_esc = np.sqrt(2 * cls.mu / params.r_p)
        else:  # Hyperbolic
            params.r_p = params.h ** 2 / cls.mu * 1 / (1 + params.e)
            params.r_a = params.h ** 2 / cls.mu * 1 / (1 - params.e)
            params.a = (np.abs(params.r_a) - params.r_p) / 2
            params.b = params.a * np.sqrt(params.e ** 2 - 1)
            params.T = np.inf
            params.v_esc = np.sqrt(2 * cls.mu / params.r_p)
            params.theta_inf = np.arccos(-1 / params.e)
            params.beta = np.arccos(1 / params.e)
            params.delta = 2 * np.arcsin(1 / params.e)
            params.Delta = params.a * np.sqrt(params.e ** 2 - 1)
            params.v_inf = np.sqrt(cls.mu / params.a)
            params.C_3 = params.v_inf ** 2

        return params
