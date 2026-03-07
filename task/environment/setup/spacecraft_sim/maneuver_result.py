"""ManeuverResult and HohmannDirection — extracted from SpacecraftSimulator/tools/OrbitalManeuvers.py"""

from enum import IntEnum
from dataclasses import dataclass, field

from spacecraft_sim.orbital_elements import OrbitalElements


class HohmannDirection(IntEnum):
    """List of Hohmann transfer directions"""

    PER2APO = 0
    APO2PER = 1
    PER2PER = 2
    APO2APO = 3


@dataclass
class ManeuverResult:
    """Maneuver parameters"""

    dv: float = 0.0              # Delta Velocity    [km/s]
    dt: float = 0.0              # Delta Time        [s]
    dm: float = 0.0              # Delta Mass        [kg]
    oe: OrbitalElements = field(default_factory=lambda: OrbitalElements())
