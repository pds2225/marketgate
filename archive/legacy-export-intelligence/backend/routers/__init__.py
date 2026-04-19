"""API routers for the export intelligence backend.

This package exposes individual routers for recommendation, simulation, and matching
features. Each router encapsulates the endpoint definitions and delegates business
logic to corresponding services.
"""

from .recommendation import router as recommendation
from .simulation import router as simulation
from .matching import router as matching

__all__ = ["recommendation", "simulation", "matching"]