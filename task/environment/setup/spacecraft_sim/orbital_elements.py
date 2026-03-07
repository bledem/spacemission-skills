"""OrbitalElements dataclass — extracted from SpacecraftSimulator/tools/ThreeDimensionalOrbit.py"""

from dataclasses import dataclass


@dataclass
class OrbitalElements:
    """Orbital elements parameters"""

    h: float = 0.0       # Specific Angular Momentum                    [km^2/s]
    e: float = 0.0       # Eccentricity                                 []
    i: float = 0.0       # Inclination                                  [rad]
    Omega: float = 0.0   # Right Ascension of the Ascending Node (RAAN) [rad]
    omega: float = 0.0   # Argument of the Perigee                      [rad]
    theta: float = 0.0   # True Anomaly                                 [rad]
    a: float = 0.0       # Semi-Major Axis                              [km]
