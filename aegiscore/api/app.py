"""Application factory and ASGI entry point for the minimal backend."""

from fastapi import FastAPI

from aegiscore.api.routes import router


def create_app() -> FastAPI:
    """Build the API without creating transports, clients, or external services."""

    app = FastAPI(title="AEGISCORE AI Backend", version="0.1.0")
    app.include_router(router)
    return app


app = create_app()
