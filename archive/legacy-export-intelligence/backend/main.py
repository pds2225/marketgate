from fastapi import FastAPI

from .routers import recommendation, simulation, matching


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns
    -------
    FastAPI
        Configured FastAPI application instance.
    """
    app = FastAPI(title="Global Export Intelligence Platform API",
                  description=(
                      "API endpoints for recommending export markets, "
                      "simulating export performance, and matching buyers and sellers. "
                      "This MVP implementation uses in‑memory data and simple rules."
                  ),
                  version="0.1.0")

    # Include API routers with prefixes
    # Routers imported from export_intelligence.backend.routers are APIRouter
    # instances; include them directly without referencing a `router` attribute.
    app.include_router(recommendation, prefix="/recommend", tags=["recommendation"])
    app.include_router(simulation, prefix="/simulate", tags=["simulation"])
    app.include_router(matching, prefix="/match", tags=["matching"])

    @app.get("/")
    async def root():
        """Root endpoint for health check."""
        return {"message": "Welcome to the Global Export Intelligence Platform API"}

    return app


app = create_app()