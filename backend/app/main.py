"""
TayAI Backend - Main Application Entry Point

Configures and starts the FastAPI application with:
- CORS middleware for frontend access
- Rate limiting middleware using Redis
- Global exception handlers
- Database initialization on startup
- Health check endpoints
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.exceptions import TayAIError, to_http_exception
from app.api.v1.router import api_router
from app.db.database import init_db
from app.middleware import RateLimitMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# Application Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting TayAI API...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down TayAI API...")


# =============================================================================
# Application Instance
# =============================================================================

app = FastAPI(
    title="TayAI API",
    description="Custom AI Assistant with Knowledge Base & Gated Access",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(TayAIError)
async def tayai_exception_handler(request: Request, exc: TayAIError):
    """Handle custom TayAI exceptions."""
    logger.error(f"TayAI Error: {exc.code} - {exc.message}")
    http_exc = to_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=exc.to_dict(),
        headers=http_exc.headers
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {"errors": errors}
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {exc}")
    
    # Don't expose internal errors in production
    message = str(exc) if settings.DEBUG else "An unexpected error occurred"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": message,
            "details": {}
        }
    )


# =============================================================================
# Middleware
# =============================================================================

# CORS Middleware (must be first for preflight requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
)

# Rate Limit Middleware
app.add_middleware(RateLimitMiddleware)

# Trusted Host Middleware (production only)
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )


# =============================================================================
# Request Logging Middleware
# =============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = datetime.utcnow()
    
    response = await call_next(request)
    
    # Calculate request duration
    duration = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    # Log request info (skip health checks)
    if request.url.path not in ["/health", "/"]:
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Duration: {duration:.2f}ms"
        )
    
    return response


# =============================================================================
# Routes
# =============================================================================

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "message": "TayAI API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.DEBUG else None
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }
