"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from hoshi.adb import ADBError
from hoshi.ephemeris import HorizonsError

from hoshi_api.routes import charts, info


def create_app() -> FastAPI:
    application = FastAPI(
        title="Hoshi API",
        description="REST API for real-sky astrological charting.",
        version="0.1.0",
    )

    application.add_exception_handler(FileNotFoundError, _not_found)
    application.add_exception_handler(FileExistsError, _conflict)
    application.add_exception_handler(ValueError, _unprocessable)
    application.add_exception_handler(HorizonsError, _bad_gateway)
    application.add_exception_handler(ADBError, _bad_gateway)

    application.include_router(charts.router)
    application.include_router(info.router)

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
