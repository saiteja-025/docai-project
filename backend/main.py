from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

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
            "  AI chat, summarisation, and quiz generation will return mock responses.\n"
            "  Set GROQ_API_KEY in your environment / Render dashboard to enable AI features."
        )
    else:
        print("[OK] GROQ_API_KEY is configured — AI features enabled.")

    if not settings.CLOUDINARY_URL:
        print(
            "[WARNING] CLOUDINARY_URL is NOT set.\n"
            "  Uploaded files will NOT be stored in the cloud (mock URLs will be used).\n"
            "  Set CLOUDINARY_URL in your environment / Render dashboard to enable cloud storage."
        )
    else:
        print("[OK] CLOUDINARY_URL is configured — cloud file storage enabled.")

    # Database Initialisation — creates tables that don't yet exist
    from backend.db.session import engine
    from backend.db.models import Base
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables verified / created.")

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
        # API routes are matched first by the routers above; this only fires
        # for non-API paths — serve the index.html SPA shell.
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
else:
    @app.get("/")
    def root():
        return {"message": "Welcome to Document Intelligence Platform API"}
