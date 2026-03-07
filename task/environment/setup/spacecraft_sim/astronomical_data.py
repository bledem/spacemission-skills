"""AstronomicalData — extracted from SpacecraftSimulator/tools/AstronomicalData.py

All planetary data, gravitational parameters, orbital elements and rates.
Original author: Alessio Negri (LGPL v3)
Reference: "Orbital Mechanics for Engineering Students" — Howard D. Curtis
"""

import numpy as np
from enum import IntEnum


# --- ENUMS ---

class CelestialBody(IntEnum):
    SUN     = 0
    MERCURY = 1
    VENUS   = 2
    EARTH   = 3
    MOON    = 4
    MARS    = 5
    JUPITER = 6
    SATURN  = 7
    URANUS  = 8
    NEPTUNE = 9
    PLUTO   = 10


class Planet(IntEnum):
    MERCURY = 0
    VENUS   = 1
    EARTH   = 2
    MARS    = 3
    JUPITER = 4
    SATURN  = 5
    URANUS  = 6
    NEPTUNE = 7
    PLUTO   = 8


# --- CONVERTERS ---

def celestial_body_from_planet(planet: Planet) -> CelestialBody:
    _map = {
        Planet.MERCURY: CelestialBody.MERCURY, Planet.VENUS: CelestialBody.VENUS,
        Planet.EARTH: CelestialBody.EARTH, Planet.MARS: CelestialBody.MARS,
        Planet.JUPITER: CelestialBody.JUPITER, Planet.SATURN: CelestialBody.SATURN,
        Planet.URANUS: CelestialBody.URANUS, Planet.NEPTUNE: CelestialBody.NEPTUNE,
        Planet.PLUTO: CelestialBody.PLUTO,
    }
    return _map.get(planet, CelestialBody.EARTH)


def celestial_body_from_index(index: int) -> CelestialBody:
    _map = {0: CelestialBody.SUN, 1: CelestialBody.MERCURY, 2: CelestialBody.VENUS,
            3: CelestialBody.EARTH, 4: CelestialBody.MOON, 5: CelestialBody.MARS,
            6: CelestialBody.JUPITER, 7: CelestialBody.SATURN, 8: CelestialBody.URANUS,
            9: CelestialBody.NEPTUNE, 10: CelestialBody.PLUTO}
    return _map.get(index, CelestialBody.EARTH)


def index_from_celestial_body(celestialBody: CelestialBody) -> int:
    _map = {CelestialBody.SUN: 0, CelestialBody.MERCURY: 1, CelestialBody.VENUS: 2,
            CelestialBody.EARTH: 3, CelestialBody.MOON: 4, CelestialBody.MARS: 5,
            CelestialBody.JUPITER: 6, CelestialBody.SATURN: 7, CelestialBody.URANUS: 8,
            CelestialBody.NEPTUNE: 9, CelestialBody.PLUTO: 10}
    return _map.get(celestialBody, 3)


def planet_from_index(index: int) -> Planet:
    _map = {0: Planet.MERCURY, 1: Planet.VENUS, 2: Planet.EARTH, 3: Planet.MARS,
            4: Planet.JUPITER, 5: Planet.SATURN, 6: Planet.URANUS, 7: Planet.NEPTUNE,
            8: Planet.PLUTO}
    return _map.get(index, Planet.EARTH)


def index_from_planet(planet: Planet) -> int:
    _map = {Planet.MERCURY: 0, Planet.VENUS: 1, Planet.EARTH: 2, Planet.MARS: 3,
            Planet.JUPITER: 4, Planet.SATURN: 5, Planet.URANUS: 6, Planet.NEPTUNE: 7,
            Planet.PLUTO: 8}
    return _map.get(planet, 2)


# --- CLASS ---

class AstronomicalData:
    """Gives access to different methods for extrapolating data of celestial bodies"""

    # --- CONSTANTS ---
    G   = 6.674_301_5e-20       # Universal Gravitational Constant  [km^3 s^2 / kg]
    AU  = 149_597_870.707       # Astronomical Unit                 [km]
    c   = 299_792_458           # Speed of Light                    [m/s]
    S_0 = 5.670e-8 * 5_777**4  # Radiated power intensity from Sun [W/m^2]
    R_0 = 696_000               # Photosphere radius                [km]

    # --- DATA TABLES (private) ---

    _equatorial_radius = {
        CelestialBody.SUN: 696_300, CelestialBody.MERCURY: 2_439.700,
        CelestialBody.VENUS: 6_051.800, CelestialBody.EARTH: 6_378.137,
        CelestialBody.MOON: 1_738.100, CelestialBody.MARS: 3_396.200,
        CelestialBody.JUPITER: 71_492, CelestialBody.SATURN: 60_268,
        CelestialBody.URANUS: 25_559, CelestialBody.NEPTUNE: 24_764,
        CelestialBody.PLUTO: 1_188.300,
    }

    _flattening = {
        CelestialBody.SUN: 0.000_050, CelestialBody.MERCURY: 0.000_900,
        CelestialBody.VENUS: 0.000_000, CelestialBody.EARTH: 1 / 298.257_222_101,
        CelestialBody.MOON: 0.001_200, CelestialBody.MARS: 0.005_890,
        CelestialBody.JUPITER: 0.064_870, CelestialBody.SATURN: 0.097_960,
        CelestialBody.URANUS: 0.022_900, CelestialBody.NEPTUNE: 0.017_100,
        CelestialBody.PLUTO: 0.010_000,
    }

    _J2 = {
        CelestialBody.SUN: 0, CelestialBody.MERCURY: 60e-6,
        CelestialBody.VENUS: 4.458e-6, CelestialBody.EARTH: 1.08263e-3,
        CelestialBody.MOON: 202.7e-6, CelestialBody.MARS: 1.96045e-3,
        CelestialBody.JUPITER: 14.736e-3, CelestialBody.SATURN: 16.298e-3,
        CelestialBody.URANUS: 3.34343e-3, CelestialBody.NEPTUNE: 3.411e-3,
        CelestialBody.PLUTO: 0,
    }

    _sidereal_period_days = {
        CelestialBody.SUN: 0,
        CelestialBody.MERCURY: 87.969_100_000,
        CelestialBody.VENUS: 224.701_000_000,
        CelestialBody.EARTH: 365.256_363_004,
        CelestialBody.MOON: 27.321_661_000,
        CelestialBody.MARS: 686.980_000_000,
        CelestialBody.JUPITER: 4_332.590_000_000,
        CelestialBody.SATURN: 10_755.700_000_000,
        CelestialBody.URANUS: 30_688.500_000_000,
        CelestialBody.NEPTUNE: 60_195.000_000_000,
        CelestialBody.PLUTO: 90_560.000_000_000,
    }

    _mass = {
        CelestialBody.SUN: 1.9885e30, CelestialBody.MERCURY: 3.3011e23,
        CelestialBody.VENUS: 4.8675e24, CelestialBody.EARTH: 5.972168e24,
        CelestialBody.MOON: 7.342e22, CelestialBody.MARS: 6.4171e23,
        CelestialBody.JUPITER: 1.8982e27, CelestialBody.SATURN: 5.6834e26,
        CelestialBody.URANUS: 8.6810e25, CelestialBody.NEPTUNE: 1.02409e26,
        CelestialBody.PLUTO: 1.303e22,
    }

    _gravity = {
        CelestialBody.SUN: 274, CelestialBody.MERCURY: 3.700,
        CelestialBody.VENUS: 8.870, CelestialBody.EARTH: 9.806_650,
        CelestialBody.MOON: 1.622, CelestialBody.MARS: 3.720_760,
        CelestialBody.JUPITER: 24.790, CelestialBody.SATURN: 10.440,
        CelestialBody.URANUS: 8.690, CelestialBody.NEPTUNE: 11.150,
        CelestialBody.PLUTO: 0.620,
    }

    # Semi-major axis in AU (except Earth in km)
    _semi_major_axis_au = {
        CelestialBody.SUN: 0, CelestialBody.MERCURY: 0.387_098,
        CelestialBody.VENUS: 0.723_332, CelestialBody.EARTH: None,
        CelestialBody.MOON: 0.002_570, CelestialBody.MARS: 1.523_680_550,
        CelestialBody.JUPITER: 5.203_800, CelestialBody.SATURN: 9.582_600,
        CelestialBody.URANUS: 19.191_260, CelestialBody.NEPTUNE: 30.070,
        CelestialBody.PLUTO: 39.482,
    }

    _gravitational_parameter = {
        CelestialBody.SUN: 132_712_440_018.9,
        CelestialBody.MERCURY: 22032.9, CelestialBody.VENUS: 324_859.9,
        CelestialBody.EARTH: 398_600.441_88, CelestialBody.MOON: 4_904.869_59,
        CelestialBody.MARS: 42_828.372, CelestialBody.JUPITER: 126_686_534.9,
        CelestialBody.SATURN: 37_931_187.9, CelestialBody.URANUS: 5_793_939.9,
        CelestialBody.NEPTUNE: 6_836_529.9, CelestialBody.PLUTO: 871.9,
    }

    # --- METHODS ---

    @classmethod
    def equatiorial_radius(cls, celestialBody: CelestialBody) -> float:
        """Equatorial Radius [km]"""
        return cls._equatorial_radius.get(celestialBody, 0)

    @classmethod
    def flattening(cls, celestialBody: CelestialBody) -> float:
        """Flattening []"""
        return cls._flattening.get(celestialBody, 0)

    @classmethod
    def second_zonal_harmonics(cls, celestialBody: CelestialBody) -> float:
        """Second Zonal Harmonics J_2 []"""
        return cls._J2.get(celestialBody, 0)

    @classmethod
    def sidereal_orbital_period(cls, celestialBody: CelestialBody) -> float:
        """Sidereal Orbital Period [s]"""
        return cls._sidereal_period_days.get(celestialBody, 0) * 86400

    @classmethod
    def angular_velocity(cls, celestialBody: CelestialBody) -> float:
        """Angular Velocity [rad/s]"""
        T = cls.sidereal_orbital_period(celestialBody)
        return 2 * np.pi / T if T > 0 else 0

    @classmethod
    def ground_track_angular_velocity(cls, celestialBody: CelestialBody) -> float:
        """Ground Track Angular Velocity [rad/s]"""
        T = cls.sidereal_orbital_period(celestialBody)
        return (2 * np.pi / T + 2 * np.pi / 86400) if T > 0 else 0

    @classmethod
    def mass(cls, celestialBody: CelestialBody) -> float:
        """Mass [kg]"""
        return cls._mass.get(celestialBody, 0)

    @classmethod
    def gravity(cls, celestialBody: CelestialBody, km: bool = False) -> float:
        """Gravity [m/s^2] or [km/s^2] if km=True"""
        g = cls._gravity.get(celestialBody, 0)
        return g * 1e-3 if km else g

    @classmethod
    def sphere_of_influence(cls, celestialBody: CelestialBody) -> float:
        """Sphere Of Influence [km]"""
        if celestialBody == CelestialBody.SUN:
            return 0
        parent = CelestialBody.EARTH if celestialBody == CelestialBody.MOON else CelestialBody.SUN
        return cls.semi_major_axis(celestialBody) * (cls.mass(celestialBody) / cls.mass(parent)) ** (2 / 5)

    @classmethod
    def semi_major_axis(cls, celestialBody: CelestialBody) -> float:
        """Semi-major axis [km]"""
        if celestialBody == CelestialBody.EARTH:
            return 149_598_023
        au_val = cls._semi_major_axis_au.get(celestialBody, 0)
        return au_val * cls.AU if au_val else 0

    @classmethod
    def eccentricity(cls, celestialBody: CelestialBody) -> float:
        """Eccentricity []"""
        _ecc = {
            CelestialBody.SUN: 0, CelestialBody.MERCURY: 0.205_630,
            CelestialBody.VENUS: 0.006_772, CelestialBody.EARTH: 0.016_708_600,
            CelestialBody.MOON: 0.054_900, CelestialBody.MARS: 0.093_400,
            CelestialBody.JUPITER: 0.048_900, CelestialBody.SATURN: 0.056_500,
            CelestialBody.URANUS: 0.047_170, CelestialBody.NEPTUNE: 0.008_678,
            CelestialBody.PLUTO: 0.2488,
        }
        return _ecc.get(celestialBody, 0)

    @classmethod
    def inclination(cls, celestialBody: CelestialBody) -> float:
        """Inclination [rad]"""
        _inc_deg = {
            CelestialBody.SUN: 0, CelestialBody.MERCURY: 7.005,
            CelestialBody.VENUS: 3.394_58, CelestialBody.EARTH: 0.00,
            CelestialBody.MOON: 5.145, CelestialBody.MARS: 1.850,
            CelestialBody.JUPITER: 1.303, CelestialBody.SATURN: 2.485,
            CelestialBody.URANUS: 0.773, CelestialBody.NEPTUNE: 1.770,
            CelestialBody.PLUTO: 17.16,
        }
        return np.deg2rad(_inc_deg.get(celestialBody, 0))

    @classmethod
    def right_ascension_of_ascending_node(cls, celestialBody: CelestialBody) -> float:
        """Right Ascension of the Ascending Node [rad]"""
        _raan_deg = {
            CelestialBody.SUN: 0, CelestialBody.MERCURY: 48.331,
            CelestialBody.VENUS: 76.680, CelestialBody.EARTH: -11.260_640,
            CelestialBody.MOON: 0, CelestialBody.MARS: 49.578_540,
            CelestialBody.JUPITER: 100.464, CelestialBody.SATURN: 113.665,
            CelestialBody.URANUS: 74.006, CelestialBody.NEPTUNE: 131.783,
            CelestialBody.PLUTO: 110.299,
        }
        return np.deg2rad(_raan_deg.get(celestialBody, 0))

    @classmethod
    def argument_perihelion(cls, celestialBody: CelestialBody) -> float:
        """Argument of Perihelion [rad]"""
        _ap_deg = {
            CelestialBody.SUN: 0, CelestialBody.MERCURY: 29.124,
            CelestialBody.VENUS: 54.884, CelestialBody.EARTH: 114.207_830,
            CelestialBody.MOON: 0, CelestialBody.MARS: 286.500,
            CelestialBody.JUPITER: 273.867, CelestialBody.SATURN: 339.392,
            CelestialBody.URANUS: 96.998_857, CelestialBody.NEPTUNE: 273.187,
            CelestialBody.PLUTO: 113.834,
        }
        return np.deg2rad(_ap_deg.get(celestialBody, 0))

    @classmethod
    def gravitational_parameter(cls, celestialBody: CelestialBody) -> float:
        """Gravitational Parameter [km^3/s^2]"""
        return cls._gravitational_parameter.get(celestialBody, 0)

    @classmethod
    def planetary_orbital_elements_and_rates(cls, celestialBody: CelestialBody) -> list:
        """Planetary Orbital Elements & Rates (JPL data, J2000 epoch)

        Returns:
            list: [orbital_elements_dict, orbital_elements_rates_dict]
        """
        oe = dict(a=0.0, e=0.0, i=0.0, Omega=0.0, bomega=0.0, L=0.0)
        doe = dict(a=0.0, e=0.0, i=0.0, Omega=0.0, bomega=0.0, L=0.0)

        if celestialBody == CelestialBody.SUN:
            return [oe, doe]

        # Data from JPL — Table 8.1 in Curtis
        _data = {
            CelestialBody.MERCURY: (
                dict(a=0.38709927, e=0.20563593, i=7.00497902, Omega=48.33076593, bomega=77.45779628, L=252.25032350),
                dict(a=0.00000037, e=0.00001906, i=-0.00594749, Omega=-0.12534081, bomega=0.16047689, L=149472.67411175),
            ),
            CelestialBody.VENUS: (
                dict(a=0.72333566, e=0.00677672, i=3.39467605, Omega=76.67984255, bomega=131.60246717, L=181.97909950),
                dict(a=0.00000390, e=-0.00004107, i=-0.00078890, Omega=-0.27769418, bomega=0.00268329, L=58517.81538729),
            ),
            CelestialBody.EARTH: (
                dict(a=1.00000261, e=0.01671123, i=-0.00001531, Omega=0.0, bomega=102.93768193, L=100.46457166),
                dict(a=0.00000562, e=-0.00004932, i=-0.01294668, Omega=0.0, bomega=0.32327364, L=35999.37244981),
            ),
            CelestialBody.MARS: (
                dict(a=1.52371034, e=0.09339410, i=1.84969142, Omega=49.55953891, bomega=360 - 23.94362959, L=360 - 4.55343205),
                dict(a=0.0001847, e=0.00007882, i=-0.00813131, Omega=-0.29257343, bomega=0.44441088, L=19140.30268499),
            ),
            CelestialBody.JUPITER: (
                dict(a=5.20288700, e=0.04838624, i=1.30439695, Omega=100.47390909, bomega=14.72847983, L=34.39644501),
                dict(a=-0.00011607, e=0.00013253, i=-0.00183714, Omega=0.20469106, bomega=0.21252668, L=3034.74612775),
            ),
            CelestialBody.SATURN: (
                dict(a=9.53667594, e=0.05386179, i=2.48599187, Omega=113.66242448, bomega=92.59887831, L=49.95424423),
                dict(a=-0.00125060, e=-0.00050991, i=0.00193609, Omega=-0.28867794, bomega=-0.41897216, L=1222.49362201),
            ),
            CelestialBody.URANUS: (
                dict(a=19.18916464, e=0.04725744, i=0.77263783, Omega=74.01692503, bomega=170.95427630, L=313.23810451),
                dict(a=-0.00196176, e=-0.00004397, i=-0.00242939, Omega=0.04240589, bomega=0.40805281, L=424.48202785),
            ),
            CelestialBody.NEPTUNE: (
                dict(a=30.06992276, e=0.00859048, i=1.77004347, Omega=131.78422574, bomega=44.96476227, L=360 - 55.12002969),
                dict(a=0.00026291, e=0.00005105, i=0.00035372, Omega=-0.00508664, bomega=-0.32241464, L=218.45945325),
            ),
            CelestialBody.PLUTO: (
                dict(a=39.48211675, e=0.24882730, i=17.14001206, Omega=110.30393684, bomega=224.06891629, L=238.92903833),
                dict(a=-0.00031596, e=0.00005170, i=0.00004818, Omega=-0.01183482, bomega=-0.04062942, L=145.20780515),
            ),
        }

        if celestialBody in _data:
            oe, doe = _data[celestialBody]

        return [oe, doe]
