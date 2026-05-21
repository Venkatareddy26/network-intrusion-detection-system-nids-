"""API middleware for security, logging, and monitoring."""

import time
import uuid
from typing import Callable

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from config import config
from src.nids.utils.exceptions import NIDSException
from src.nids.utils.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()

        # Log request
        logger.info(
            "Incoming request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
                exc_info=True,
            )
            raise


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication."""

    def __init__(self, app, exempt_paths: list = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or ["/", "/health", "/docs", "/openapi.json", "/redoc"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip authentication for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Skip if API key authentication is disabled
        if not config.security.require_api_key:
            return await call_next(request)

        # Check API key
        api_key = request.headers.get(config.security.api_key_header)

        if not api_key:
            logger.warning(
                "Missing API key",
                extra={
                    "client_ip": request.client.host if request.client else "unknown",
                    "path": request.url.path,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "API key required", "error_code": "AUTH_FAILED"},
            )

        if api_key not in config.security.api_keys:
            logger.warning(
                "Invalid API key",
                extra={
                    "client_ip": request.client.host if request.client else "unknown",
                    "path": request.url.path,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "Invalid API key", "error_code": "AUTH_FAILED"},
            )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""

    def __init__(self, app, requests_per_minute: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}
        self.window_start = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Reset window if needed
        if client_ip not in self.window_start or current_time - self.window_start[client_ip] >= 60:
            self.window_start[client_ip] = current_time
            self.request_counts[client_ip] = 0

        # Check rate limit
        self.request_counts[client_ip] += 1

        if self.request_counts[client_ip] > self.requests_per_minute:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "requests": self.request_counts[client_ip],
                },
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "retry_after": 60 - int(current_time - self.window_start[client_ip]),
                },
            )

        return await call_next(request)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized error handling."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except NIDSException as e:
            logger.error(
                f"NIDS exception: {e.message}",
                extra={
                    "error_code": e.error_code,
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": e.message, "error_code": e.error_code},
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Unhandled exception: {str(e)}",
                extra={
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
                exc_info=True,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "error_code": "INTERNAL_ERROR",
                },
            )


def setup_middleware(app):
    """Setup all middleware for the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # CORS
    if config.security.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.security.allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Custom middleware (order matters - last added is executed first)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=1000)
    app.add_middleware(APIKeyMiddleware)

    logger.info("Middleware configured successfully")
