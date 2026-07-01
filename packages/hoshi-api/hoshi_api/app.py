"""FastAPI application factory."""

from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from hoshi.adb import ADBError
from hoshi.ephemeris import HorizonsError

from hoshi_api.mcp_server import mcp
from hoshi_api.routes import charts, info


async def _normalize_mcp_path(request: Request, call_next):
    # Starlette's Router redirects /mcp → /mcp/ (trailing-slash redirect) for
    # mounted sub-apps.  Rewrite the path before routing so the mount matches
    # directly — no round-trip redirect for the MCP client.
    if request.url.path == "/mcp":
        request.scope["path"] = "/mcp/"
    return await call_next(request)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    sm = mcp.session_manager
    # Lambda (and TestClient) re-enters the lifespan on every invocation/test.
    # session_manager.run() permanently sets _has_started=True after its first
    # exit, raising on subsequent calls.  _task_group is None at this point
    # (the previous task group has already been torn down), so resetting
    # _has_started is safe — no live group is in flight.
    if sm._has_started and sm._task_group is None:
        sm._has_started = False
    async with sm.run():
        yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Hoshi API",
        description="REST API for real-sky astrological charting.",
        version=version("hoshi-api"),
        lifespan=_lifespan,
    )

    application.add_middleware(BaseHTTPMiddleware, dispatch=_normalize_mcp_path)

    application.add_exception_handler(FileNotFoundError, _not_found)
    application.add_exception_handler(FileExistsError, _conflict)
    application.add_exception_handler(ValueError, _unprocessable)
    application.add_exception_handler(HorizonsError, _bad_gateway)
    application.add_exception_handler(ADBError, _bad_gateway)

    application.include_router(charts.router)
    application.include_router(info.router)

    # streamable_http_app() lazily creates the session_manager used in _lifespan.
    # Mount the resulting ASGI app at /mcp; streamable_http_path="/" on the
    # FastMCP instance means the endpoint is at the sub-app root so the full
    # path is /mcp (not /mcp/mcp).
    application.mount("/mcp", mcp.streamable_http_app())

    return application


def _not_found(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def _conflict(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


def _unprocessable(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


def _bad_gateway(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


app = create_app()
