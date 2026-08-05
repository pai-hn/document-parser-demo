"""FastAPI 애플리케이션 팩토리.

``create_app()``을 통해 FastAPI 인스턴스를 생성하며,
DI 컨테이너 초기화, 예외 핸들러 등록, 미들웨어 설정, 라우터 마운트를
한 곳에서 관리합니다.

Usage::

    # 직접 실행
    uvicorn webapp.app:app --port 8080 --reload

    # 테스트에서 커스텀 컨테이너 주입
    app = create_app(container=test_container)
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.common.exceptions import AppException
from src.user.domains import User
from src.user.password import hash_password
from src.utils import new_uuid, utc_now
from webapp.container import ApplicationContainer, create_container

logger = logging.getLogger(__name__)


async def _seed_master(container: ApplicationContainer) -> None:
    """최초 실행 시 master 계정이 없으면 자동으로 생성한다.

    기본 비밀번호는 ``master``이며, ``must_change_password=True``로 설정되어
    첫 로그인 시 비밀번호 변경을 유도합니다.
    """
    user_repo = container.user.user_repo()
    existing = await user_repo.find_by_username("master")
    if existing is not None:
        return

    now = utc_now()
    master = User(
        user_id=new_uuid(),
        username="master",
        hashed_password=hash_password("master"),
        role="master",
        team_id=None,
        is_active=True,
        must_change_password=True,
        display_name="System Master",
        created_at=now,
        updated_at=now,
    )
    await user_repo.create(master)
    logger.info("Master account seeded")


def _register_exception_handlers(app: FastAPI) -> None:
    """전역 예외 핸들러를 등록한다."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "message": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"error_code": "VALIDATION_ERROR", "message": "Request validation failed", "detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred", "detail": None},
        )


def create_app(container: ApplicationContainer | None = None) -> FastAPI:
    """FastAPI 앱 인스턴스를 생성한다."""
    app_container = container or create_container()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.container = app_container  # type: ignore[attr-defined]
        import src.sample.entities  # noqa: F401
        import src.user.entities  # noqa: F401

        try:
            sf = app_container.database.session_factory()
            await asyncio.wait_for(sf.create_database(), timeout=15)
            logger.info("Database tables ensured")
        except Exception:
            logger.warning("DB table creation skipped", exc_info=True)
        try:
            await asyncio.wait_for(_seed_master(app_container), timeout=10)
        except Exception:
            logger.warning("Seed master skipped (DB unavailable)", exc_info=True)
        yield

    app = FastAPI(
        title="My Test Project",
        lifespan=lifespan,
        root_path="/api",
        generate_unique_id_function=lambda route: route.name,
    )

    _register_exception_handlers(app)

    from starlette.middleware.gzip import GZipMiddleware

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,  # type: ignore[call-arg]
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from webapp.routers import account, admin, auth, health, sample

    app.include_router(health.router, tags=["health"])
    app.include_router(auth.router, tags=["auth"])
    app.include_router(account.router, tags=["account"])
    app.include_router(admin.router, tags=["admin"])
    app.include_router(sample.router, tags=["sample"])

    return app
