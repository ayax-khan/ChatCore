from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.api.v1 import auth, sites, chat, analytics, ws, users, feedback, billing, api_keys, security
from app.utils.rate_limiter import limiter
from app.utils.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    from app.services.cache_service import CacheService
    cache = CacheService()
    await cache.init()
    yield
    await cache.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(sites.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(ws.router)
app.include_router(users.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(api_keys.router, prefix="/api/v1")
app.include_router(security.router, prefix="/api/v1")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    from prometheus_client import generate_latest
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/api/v1/config/theme")
async def get_theme():
    return {
        "primary_color": "#3b82f6",
        "logo_url": None,
        "dark_mode": False,
    }
