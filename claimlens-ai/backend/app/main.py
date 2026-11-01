from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from .api.routes import router
from .db.session import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="ClaimLens AI", version="0.1.0")
    app.include_router(router)

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return app


app = create_app()
