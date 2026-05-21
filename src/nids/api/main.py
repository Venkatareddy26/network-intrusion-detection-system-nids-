"""Compatibility entry point for the production FastAPI app.

Use ``src.nids.api.main_v2:app`` for new deployments. This module keeps older
``src.nids.api.main:app`` commands working while avoiding a second divergent API
implementation.
"""

from config import config
from src.nids.api.main_v2 import app

__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.nids.api.main:app",
        host=config.api.host,
        port=config.api.port,
        workers=config.api.workers,
        reload=config.api.reload,
        log_level=config.logging.level.lower(),
    )
