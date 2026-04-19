# Make services package importable.

"""
Service layer for the export intelligence backend.

This package groups the logic for recommendations, simulation, and matching.
Each submodule provides a function or class implementing the business rules
for its respective feature. Keeping logic separated from the FastAPI router
modules promotes testability and modularity.
"""