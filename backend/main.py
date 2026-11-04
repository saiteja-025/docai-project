import os
import sys
import time
from contextlib import asynccontextmanager

# ---------------------------------------------------------------------------
# Python Path Bootstrap:
# Guarantees that absolute package imports (`from backend.core...`) resolve
# regardless of whether the server is started from the project root:
#   `uvicorn backend.main:app`
# or from inside the backend directory:
#   `uvicorn main:app` (e.g. Render Root Directory = backend)
# ---------------------------------------------------------------------------
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)

if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.core.config import settings


# ---------------------------------------------------------------------------
# Lifespan: runs once at startup and once at shutdown.
# Handles credential validation and FAISS index restore from the database.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    print("=" * 60)
    print(f"  {settings.PROJECT_NAME}  v{settings.VERSION}")
    print("=" * 60)

    # Credential validation — surface missing keys clearly in logs
    if not settings.GROQ_API_KEY:
        print(
            "[WARNING] GROQ_API_KEY is NOT set.\n"
            "  AI features (Chat, Summarisation, Quizzes) require a valid Groq API key.\n"
            "  Provide GROQ_API_KEY in your environment to enable real Groq LLM functionality."
        )
    else:
        print("[OK] GROQ_API_KEY is configured — AI features enabled.")

    has_cloudinary = bool(
        settings.CLOUDINARY_URL or
        os.environ.get("CLOUDINARY_URL") or
        (os.environ.get("CLOUDINARY_CLOUD_NAME") and os.environ.get("CLOUDINARY_API_KEY"))
    )
    if not has_cloudinary:
        print(
            "[WARNING] Cloudinary credentials are NOT set.\n"
            "  PDF cloud uploads require valid Cloudinary credentials.\n"
            "  Set CLOUDINARY_URL or CLOUDINARY_CLOUD_NAME/KEY/SECRET in environment."
        )
    else:
        print("[OK] Cloudinary is configured — cloud file storage enabled.")

    # Database Initialisation — creates tables that don't yet exist (with retry for cold starts)
    from backend.db.session import engine
    from backend.db.models import Base
    for attempt in range(1, 6):
        try:
            Base.metadata.create_all(bind=engine)
            print("[OK] Database tables verified / created.")
            break
        except Exception as e:
            if attempt == 5:
                print(f"[ERROR] Could not connect to database after 5 attempts: {e}")
                raise
            print(f"[RETRY] Database not ready yet ({e}). Retrying in 2s ({attempt}/5)...")
            time.sleep(2)

    # Rebuild FAISS index from PostgreSQL (C2 fix: free persistence across restarts)
    from backend.services.rag_service import rebuild_faiss_index_from_db
    rebuild_faiss_index_from_db()

    print("[OK] Startup complete — serving requests.")
    print("=" * 60)

    yield  # Application runs here

    # --- Shutdown (nothing to clean up) ---
    print("[INFO] Application shutting down.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS — permissive for the unified same-origin Docker deployment.
# In this setup the SPA is served by FastAPI itself, so cross-origin
# requests only come from local development (localhost:5173).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check
@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", tags=["Health"])
def health_check():
    has_cloudinary = bool(
        settings.CLOUDINARY_URL or
        os.environ.get("CLOUDINARY_URL") or
        (os.environ.get("CLOUDINARY_CLOUD_NAME") and os.environ.get("CLOUDINARY_API_KEY"))
    )
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "groq_configured": bool(settings.GROQ_API_KEY),
        "cloudinary_configured": has_cloudinary,
    }

# Routers
from backend.api.routes import auth, documents, chat, quiz, dashboard

app.include_router(auth.router,       prefix=f"{settings.API_V1_STR}/auth",      tags=["Auth"])
app.include_router(documents.router,  prefix=f"{settings.API_V1_STR}/documents",  tags=["Documents"])
app.include_router(chat.router,       prefix=f"{settings.API_V1_STR}/chat",       tags=["Chat"])
app.include_router(quiz.router,       prefix=f"{settings.API_V1_STR}/quiz",       tags=["Quiz"])
app.include_router(dashboard.router,  prefix=f"{settings.API_V1_STR}/dashboard",  tags=["Dashboard"])

# ---------------------------------------------------------------------------
# Serve compiled React SPA (built by Docker multi-stage build)
# ---------------------------------------------------------------------------
frontend_dist = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "frontend", "dist"
)

if os.path.exists(frontend_dist):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(frontend_dist, "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # API routes are matched first by the routers above; if an unhandled /api path reaches here, 404
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
else:
    @app.get("/")
    def root():
        return {"message": "Welcome to Document Intelligence Platform API"}
