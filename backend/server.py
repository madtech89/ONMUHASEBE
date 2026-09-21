import os
import logging
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Must import models BEFORE create_all
import app.models  # noqa: F401 - registers all SQLAlchemy models

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import engine
from app.core.security import limiter
from app.models.base import Base
from app.api import auth, tenants, users, roles, modules, documents, audit_log, super_admin
from fastapi import APIRouter

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _ensure_mariadb_running():
    """Start MariaDB if not already running (development environment)."""
    try:
        result = subprocess.run(
            ["mysqladmin", "-u", "root", "ping", "--silent"],
            capture_output=True, timeout=3
        )
        if result.returncode == 0:
            return
    except Exception:
        pass
    logger.info("Starting MariaDB...")
    try:
        subprocess.Popen(
            ["mysqld_safe", "--user=mysql"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import time
        time.sleep(4)
        logger.info("MariaDB started")
    except Exception as e:
        logger.warning(f"Could not start MariaDB: {e}")


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}...")
    _ensure_mariadb_running()

    # Create all tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ready")
    except Exception as e:
        logger.error(f"Database init failed: {e}")
        raise

    # Storage directory
    os.makedirs(settings.STORAGE_LOCAL_PATH, exist_ok=True)

    # Seed
    from app.core.database import AsyncSessionLocal
    from seeds import seed_database
    try:
        async with AsyncSessionLocal() as db:
            await seed_database(db)
    except Exception as e:
        logger.error(f"Seed failed: {e}", exc_info=True)

    yield
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — same-domain in production (Emergent ingress), allow localhost for dev
cors_origins = [
    "https://kitchen-admin-suite.preview.emergentagent.com",
    "http://localhost:3000",
    "http://localhost:3001",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API router
api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(modules.router, prefix="/modules", tags=["Modules"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(audit_log.router, prefix="/audit", tags=["Audit"])
api_router.include_router(super_admin.router, prefix="/super-admin", tags=["Super Admin"])


@api_router.get("/")
async def root():
    return {"service": settings.APP_NAME, "version": "1.0.0-phase1", "status": "ok"}


@api_router.get("/health")
async def health():
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)[:100]}"
    return {"status": "ok", "database": db_status}


app.include_router(api_router)
