"""Common utility functions — extracted from SpacecraftSimulator/tools/Common.py"""

import math
import numpy as np
from datetime import datetime, timedelta


def wrap_to_2pi(x: float) -> float:
    """Wraps the angle in the range 0 - 2 PI"""
    return np.remainder(x, 2 * np.pi if x > 0 else -2 * np.pi)


def wrap_to360deg(x: float) -> float:
    """Wraps the angle in the range 0 - 360 degrees"""
    return np.remainder(x, 360 if x > 0 else -360)


def daterange(start: datetime, end: datetime, step: int = 1):
    """Generator to loop over dates from start to end with given step in days."""
    for day in range(0, int((end - start).days + 1), step):
        yield start + timedelta(day)


def daterange_length(start: datetime, end: datetime, step: int = 1) -> int:
    """Length of the daterange."""
    return math.ceil(int((end - start).days + 1) / step)
