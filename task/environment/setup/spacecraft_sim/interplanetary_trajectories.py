"""InterplanetaryTrajectories — extracted from SpacecraftSimulator/tools/InterplanetaryTrajectories.py

Interplanetary mission design: ephemeris, Lambert-based transfers, flybys, departures, arrivals.
Plotting removed for headless use. Pork chop returns data instead of plotting.

Original author: Alessio Negri (LGPL v3)
Reference: "Orbital Mechanics for Engineering Students" — Howard D. Curtis, Chapter 8
"""

import numpy as np
from enum import IntEnum
from datetime import datetime

from spacecraft_sim.common import wrap_to360deg, daterange, daterange_length
from spacecraft_sim.astronomical_data import AstronomicalData, CelestialBody
from spacecraft_sim.time_utils import Time, DirectionType
from spacecraft_sim.three_dimensional_orbit import ThreeDimensionalOrbit
from spacecraft_sim.orbital_maneuvers import OrbitalManeuvers
from spacecraft_sim.maneuver_result import ManeuverResult
from spacecraft_sim.orbital_elements import OrbitalElements
from spacecraft_sim.orbit_determination import OrbitDetermination


class FlybySide(IntEnum):
    DARK_SIDE = 0
    SUNLIT_SIDE = 1


class InterplanetaryTrajectories:
    """Implements methods and functions to simulate interplanetary trajectories"""

    # --- Section 8.3: Synodic period ---

    @classmethod
    def synodic_period(cls, departurePlanet: CelestialBody, arrivalPlanet: CelestialBody) -> float:
        """Calculates the Synodic Period for an interplanetary transfer [s]"""
        n_1 = 2 * np.pi / AstronomicalData.sidereal_orbital_period(departurePlanet)
        n_2 = 2 * np.pi / AstronomicalData.sidereal_orbital_period(arrivalPlanet)
        return 2 * np.pi / np.abs(n_2 - n_1)

    @classmethod
    def wait_time(cls, departurePlanet: CelestialBody, arrivalPlanet: CelestialBody) -> list:
        """Calculates the wait time for an interplanetary transfer.
        Returns: [wait_time_s, initial_phase_angle, final_phase_angle]
        """
        mu_sun = AstronomicalData.gravitational_parameter(CelestialBody.SUN)
        R_1 = AstronomicalData.semi_major_axis(departurePlanet)
        R_2 = AstronomicalData.semi_major_axis(arrivalPlanet)
        n_1 = 2 * np.pi / AstronomicalData.sidereal_orbital_period(departurePlanet)
        n_2 = 2 * np.pi / AstronomicalData.sidereal_orbital_period(arrivalPlanet)

        t_12 = np.pi / np.sqrt(mu_sun) * ((R_1 + R_2) / 2) ** (3 / 2)
        phi_0 = np.pi - n_2 * t_12
        phi_f = np.pi - n_1 * t_12
        phi_0 = -phi_f  # return trip initial phase angle

        t_wait = -1
        N = 0
        while t_wait < 0:
            if n_1 > n_2:
                t_wait = (-2 * phi_f - 2 * np.pi * N) / (n_2 - n_1)
            else:
                t_wait = (-2 * phi_f + 2 * np.pi * N) / (n_2 - n_1)
            N += 1

        return [t_wait, phi_0, phi_f]

    # --- Section 8.6: Departure ---

    @classmethod
    def departure(cls, departurePlanet: CelestialBody, arrivalPlanet: CelestialBody,
                  r_p: float, m: float) -> ManeuverResult:
        """Planetary departure hyperbola design (Hohmann-based v_inf estimate)"""
        mu_sun = AstronomicalData.gravitational_parameter(CelestialBody.SUN)
        mu_1 = AstronomicalData.gravitational_parameter(departurePlanet)
        R_1 = AstronomicalData.semi_major_axis(departurePlanet)
        R_2 = AstronomicalData.semi_major_axis(arrivalPlanet)

        v_inf = np.sqrt(mu_sun / R_1) * (np.sqrt(2 * R_2 / (R_1 + R_2)) - 1)
        e = 1 + r_p * v_inf ** 2 / mu_1
        h = r_p * np.sqrt(v_inf ** 2 + 2 * mu_1 / r_p)
        v_p = h / r_p
        v_c = np.sqrt(mu_1 / r_p)

        result = ManeuverResult()
        result.dv = np.abs(v_p - v_c)
        result.dt = 0.0
        result.dm = OrbitalManeuvers.propellant_mass(m, result.dv)
        result.oe = OrbitalElements(h, e, 0, 0, 0, 0, 0)
        return result

    # --- Section 8.8: Rendezvous (arrival) ---

    @classmethod
    def rendezvous(cls, departurePlanet: CelestialBody, arrivalPlanet: CelestialBody,
                   r_p_A: float, T: float, m: float) -> ManeuverResult:
        """Planetary arrival hyperbola design"""
        mu_sun = AstronomicalData.gravitational_parameter(CelestialBody.SUN)
        mu_2 = AstronomicalData.gravitational_parameter(arrivalPlanet)
        R_1 = AstronomicalData.semi_major_axis(departurePlanet)
        R_2 = AstronomicalData.semi_major_axis(arrivalPlanet)

        v_inf = np.sqrt(mu_sun / R_2) * (1 - np.sqrt(2 * R_1 / (R_1 + R_2)))

        a = (T * np.sqrt(mu_2) / (2 * np.pi)) ** (2 / 3)
        e = 1 - r_p_A / a if r_p_A != 0 else (2 * mu_2) / (a * v_inf ** 2) - 1
        r_p = r_p_A if r_p_A != 0 else 2 * mu_2 / v_inf ** 2 * (1 - e) / (1 + e)
        v_c = np.sqrt(mu_2 * (1 + e) / r_p)

        e_hyp = 1 + r_p * v_inf ** 2 / mu_2
        h_hyp = r_p * np.sqrt(v_inf ** 2 + 2 * mu_2 / r_p)
        v_p = h_hyp / r_p

        result = ManeuverResult()
        result.dv = np.abs(v_p - v_c)
        result.dt = 0.0
        result.dm = OrbitalManeuvers.propellant_mass(m, result.dv)
        result.oe = OrbitalElements(h_hyp, e_hyp, 0, 0, 0, 0, 0)
        return result

    # --- Section 8.9: Flyby ---

    @classmethod
    def flyby(cls, departurePlanet: CelestialBody, arrivalPlanet: CelestialBody,
              r_p: float, theta_1: float, m: float,
              side: FlybySide = FlybySide.DARK_SIDE) -> ManeuverResult:
        """Planetary flyby hyperbola design"""
        mu_sun = AstronomicalData.gravitational_parameter(CelestialBody.SUN)
        mu_2 = AstronomicalData.gravitational_parameter(arrivalPlanet)
        R_1 = AstronomicalData.semi_major_axis(departurePlanet)
        R_2 = AstronomicalData.semi_major_axis(arrivalPlanet)

        # Preflyby ellipse (orbit 1)
        e_1 = (R_1 - R_2) / (R_1 + R_2 * np.cos(theta_1))
        h_1 = np.sqrt(mu_sun * R_1 * (1 - e_1))
        V_t_1 = mu_sun / h_1 * (1 + e_1 * np.cos(theta_1))
        V_r_1 = mu_sun / h_1 * e_1 * np.sin(theta_1)

        V_1_v = np.array([V_t_1, -V_r_1])
        V_2 = np.array([np.sqrt(mu_sun / R_2), 0])
        v_inf_1 = V_1_v - V_2
        v_inf_m = np.linalg.norm(v_inf_1)

        e = 1 + r_p * v_inf_m ** 2 / mu_2
        h = r_p * np.sqrt(v_inf_m ** 2 + 2 * mu_2 / r_p)
        delta = 2 * np.arcsin(1 / e)
        phi_1 = np.arctan(v_inf_1[1] / v_inf_1[0])

        # Approach
        phi_2 = phi_1 + delta if side == FlybySide.DARK_SIDE else phi_1 - delta
        v_inf_2 = np.array([v_inf_m * np.cos(phi_2), v_inf_m * np.sin(phi_2)])
        V_2_v = V_2 + v_inf_2
        V_t_2 = V_2_v[0]
        V_r_2 = -V_2_v[1]

        # Postflyby ellipse (orbit 2)
        h_2 = R_2 * V_t_2
        e_cos = h_2 ** 2 / (mu_sun * R_2) - 1
        e_sin = V_r_2 * h_2 / mu_sun
        theta_2 = np.arctan2(e_sin, e_cos)
        e_2 = e_sin / np.sin(theta_2)

        result = ManeuverResult()
        result.dv = 0.0
        result.dt = 0.0
        result.dm = OrbitalManeuvers.propellant_mass(m, result.dv)
        result.oe = OrbitalElements(h_2, e_2, 0, 0, 0, 0, 0)
        return result

    # --- Algorithm 8.1: Ephemeris ---

    @classmethod
    def ephemeris(cls, planet: CelestialBody, date: datetime) -> list:
        """Evaluates the ephemeris for a given planet and date.
        Returns: [r_GEF, v_GEF] (heliocentric position and velocity vectors in km, km/s)
        """
        mu_sun = AstronomicalData.gravitational_parameter(CelestialBody.SUN)
        JD = OrbitDetermination.julian_day(date.year, date.month, date.day, date.hour, date.minute, date.second)
        T_0 = (JD - 2_451_545) / 36_525

        oe, doe_dt = AstronomicalData.planetary_orbital_elements_and_rates(planet)

        a = (oe['a'] + doe_dt['a'] * T_0) * AstronomicalData.AU
        e = oe['e'] + doe_dt['e'] * T_0
        i = wrap_to360deg(oe['i'] + doe_dt['i'] * T_0)
        Omega = wrap_to360deg(oe['Omega'] + doe_dt['Omega'] * T_0)
        bomega = wrap_to360deg(oe['bomega'] + doe_dt['bomega'] * T_0)
        L = wrap_to360deg(oe['L'] + doe_dt['L'] * T_0)

        T = 2 * np.pi * np.sqrt(a ** 3 / mu_sun)
        h = np.sqrt(mu_sun * a * (1 - e ** 2))

        omega = bomega - Omega
        M = L - bomega
        t = np.deg2rad(M) * T / (2 * np.pi)
        theta = Time.calculate_elliptical_orbit(DirectionType.TIME_TO_MEAN_ANOMALY, T=T, e=e, t=t)

        ThreeDimensionalOrbit.set_celestial_body(CelestialBody.SUN)
        return ThreeDimensionalOrbit.pf_2_gef(
            OrbitalElements(h, e, np.deg2rad(i), np.deg2rad(Omega), np.deg2rad(omega), theta, a)
        )

    # --- Algorithm 8.2: Optimal transfer with Lambert ---

    @classmethod
    def optimal_transfer(cls,
                         departurePlanet: CelestialBody,
                         arrivalPlanet: CelestialBody,
                         departureDate: datetime,
                         arrivalDate: datetime,
                         r_p_D: float,
                         r_p_A: float,
                         T: float,
                         m: float) -> list:
        """Optimal transfer with Lambert problem.
        Returns: [maneuver_departure, maneuver_arrival, lambert_orbital_elements, lambert_theta_2]
        """
        R_1, V_1 = cls.ephemeris(departurePlanet, departureDate)
        R_2, V_2 = cls.ephemeris(arrivalPlanet, arrivalDate)
        dt = (arrivalDate - departureDate).total_seconds()

        OrbitDetermination.set_celestial_body(CelestialBody.SUN)
        V_D_v, V_A_v, oe, theta_2 = OrbitDetermination.solve_lambert_problem(R_1, R_2, dt)

        v_inf_D = V_D_v - V_1
        v_inf_A = V_A_v - V_2

        # Departure
        mu_D = AstronomicalData.gravitational_parameter(departurePlanet)
        e_dep = 1 + r_p_D * np.linalg.norm(v_inf_D) ** 2 / mu_D
        h_dep = r_p_D * np.sqrt(np.linalg.norm(v_inf_D) ** 2 + 2 * mu_D / r_p_D)
        v_p_dep = h_dep / r_p_D
        v_c_dep = np.sqrt(mu_D / r_p_D)

        maneuver_1 = ManeuverResult()
        maneuver_1.dv = np.abs(v_p_dep - v_c_dep)
        maneuver_1.dt = 0.0
        maneuver_1.dm = OrbitalManeuvers.propellant_mass(m, maneuver_1.dv)
        maneuver_1.oe = OrbitalElements(h_dep, e_dep, 0, 0, 0, 0, 0)

        # Arrival
        mu_A = AstronomicalData.gravitational_parameter(arrivalPlanet)
        a_arr = (T * np.sqrt(mu_A) / (2 * np.pi)) ** (2 / 3)
        e_arr = 1 - r_p_A / a_arr if r_p_A != 0 else (2 * mu_A) / (a_arr * np.linalg.norm(v_inf_A) ** 2) - 1
        r_p_arr = r_p_A if r_p_A != 0 else 2 * mu_A / np.linalg.norm(v_inf_A) ** 2 * (1 - e_arr) / (1 + e_arr)
        v_c_arr = np.sqrt(mu_A * (1 + e_arr) / r_p_arr)

        e_hyp = 1 + r_p_arr * np.linalg.norm(v_inf_A) ** 2 / mu_A
        h_hyp = r_p_arr * np.sqrt(np.linalg.norm(v_inf_A) ** 2 + 2 * mu_A / r_p_arr)
        v_p_arr = h_hyp / r_p_arr

        maneuver_2 = ManeuverResult()
        maneuver_2.dv = np.abs(v_p_arr - v_c_arr)
        maneuver_2.dt = 0.0
        maneuver_2.dm = OrbitalManeuvers.propellant_mass(m, maneuver_2.dv)
        maneuver_2.oe = OrbitalElements(h_hyp, e_hyp, 0, 0, 0, 0, 0)

        return [maneuver_1, maneuver_2, oe, theta_2]

    # --- Pork chop plot (data only, no plotting) ---

    @classmethod
    def pork_chop(cls,
                  departurePlanet: CelestialBody,
                  arrivalPlanet: CelestialBody,
                  launchWindow: list,
                  arrivalWindow: list,
                  step: int = 1) -> dict:
        """Evaluates the pork chop data for the transfer.
        Returns dict with keys: dv_departure, dv_arrival, time_of_flight, launch_dates, arrival_dates
        """
        lwBeg, lwEnd = launchWindow
        awBeg, awEnd = arrivalWindow

        n_aw = daterange_length(awBeg, awEnd, step)
        n_lw = daterange_length(lwBeg, lwEnd, step)

        dv_1 = np.zeros((n_aw, n_lw))
        dv_2 = np.zeros((n_aw, n_lw))
        T_F = np.zeros((n_aw, n_lw))
        launch_dates = []
        arrival_dates = []

        for lwIndex, lwDate in enumerate(daterange(lwBeg, lwEnd, step)):
            if lwIndex == 0:
                launch_dates = []
            launch_dates.append(lwDate)
            for awIndex, awDate in enumerate(daterange(awBeg, awEnd, step)):
                if lwIndex == 0:
                    arrival_dates.append(awDate)

                R_1, V_1 = cls.ephemeris(departurePlanet, lwDate)
                R_2, V_2 = cls.ephemeris(arrivalPlanet, awDate)
                dt = (awDate - lwDate).total_seconds()
                T_F[awIndex, lwIndex] = dt / 3600 / 24

                OrbitDetermination.set_celestial_body(CelestialBody.SUN)
                V_D_v, V_A_v, oe, theta_2 = OrbitDetermination.solve_lambert_problem(R_1, R_2, dt)

                dv_1[awIndex, lwIndex] = np.linalg.norm(V_D_v - V_1)
                dv_2[awIndex, lwIndex] = np.linalg.norm(V_A_v - V_2)

        return {
            "dv_departure": dv_1,
            "dv_arrival": dv_2,
            "dv_total": dv_1 + dv_2,
            "time_of_flight_days": T_F,
            "launch_dates": launch_dates,
            "arrival_dates": arrival_dates,
        }
