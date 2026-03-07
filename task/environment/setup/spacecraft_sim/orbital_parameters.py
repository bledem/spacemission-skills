"""OrbitalParameters dataclass — extracted from SpacecraftSimulator/tools/TwoBodyProblem.py"""

from dataclasses import dataclass


@dataclass
class OrbitalParameters:
    """Parameters of an orbit"""

    h: float = 0.0           # Specific Angular Momentum     [km^2/s]
    epsilon: float = 0.0     # Specific Mechanical Energy    [km^2/s^2]
    e: float = 0.0           # Eccentricity                  []
    T: float = 0.0           # Orbital Period                [s]
    r_a: float = 0.0         # Apoapsis Radius               [km]
    r_p: float = 0.0         # Periapsis Radius              [km]
    a: float = 0.0           # Semi-Major Axis               [km]
    b: float = 0.0           # Semi-Minor Axis               [km]
    v_esc: float = 0.0       # Escape Velocity               [km/s]
    theta_inf: float = 0.0   # Infinite True Anomaly         [rad]
    beta: float = 0.0        # Hyperbola Asymptote Angle     [rad]
    delta: float = 0.0       # Turn Angle                    [rad]
    Delta: float = 0.0       # Aiming Radius                 [km]
    v_inf: float = 0.0       # Hyperbolic Excess Speed       [km/s]
    C_3: float = 0.0         # Characteristic Energy         [km^2/s^2]
