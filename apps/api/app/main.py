import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.auth import AuthError, router
from app.config import Settings


def create_app(settings: Settings | None = None, engine=None) -> FastAPI:
    config = settings or Settings()
    db_engine = engine if engine is not None else create_engine(config.database_url, pool_pre_ping=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        db_engine.dispose()

    app = FastAPI(title="ProofAI", version="0.1.0", lifespan=lifespan)
    app.state.config = config
    app.state.sessions = sessionmaker(db_engine, expire_on_commit=False)
    app.add_middleware(CORSMiddleware, allow_origins=[config.app_origin],
                       allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        # Browser requests may only use the configured frontend origin.
        origin = request.headers.get("origin")
        if origin and origin != config.app_origin:
            return error(request, "INVALID_ORIGIN", "This origin is not allowed.", 403)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        return response

    def error(request: Request, code: str, message: str, status: int):
        return JSONResponse(status_code=status, content={"error": {
            "code": code, "message": message, "requestId": request.state.request_id}},
            headers={"Cache-Control": "no-store"})

    @app.exception_handler(AuthError)
    async def auth_error(request: Request, exc: AuthError):
        return error(request, exc.code, exc.message, exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return error(request, "INVALID_REQUEST", "Check the wallet address, challenge ID, and signature format.", 422)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        return error(request, "DATABASE_UNAVAILABLE", "Sign-in is temporarily unavailable. Please try again.", 503)

    app.include_router(router, prefix="/api/v1")

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "feature": "wallet-auth"}

    return app
