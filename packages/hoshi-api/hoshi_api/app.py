"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from hoshi.adb import ADBError
from hoshi.ephemeris import HorizonsError

from hoshi_api.mcp_server import mcp
from hoshi_api.routes import charts, info


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    # Run the MCP session manager within the app lifespan so the mounted
    # sub-app's task group is initialized before the first request arrives.
    # In stateless_http=True mode the session_manager may not exist; guard
    # defensively so both stateful and stateless builds work correctly.
    if hasattr(mcp, "session_manager"):
        async with mcp.session_manager.run():
            yield
    else:
        yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Hoshi API",
        description="REST API for real-sky astrological charting.",
        version="0.1.0",
        lifespan=_lifespan,
    )

    application.add_exception_handler(FileNotFoundError, _not_found)
    application.add_exception_handler(FileExistsError, _conflict)
    application.add_exception_handler(ValueError, _unprocessable)
    application.add_exception_handler(HorizonsError, _bad_gateway)
    application.add_exception_handler(ADBError, _bad_gateway)

    application.include_router(charts.router)
    application.include_router(info.router)

    # Mount the MCP Streamable HTTP transport at /mcp.
    # streamable_http_path="/" on the FastMCP instance means the MCP endpoint
    # is at the root of this sub-app, so the full path is /mcp (not /mcp/mcp).
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
