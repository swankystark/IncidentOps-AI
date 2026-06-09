from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base, ensure_sqlite_schema
from .routes import config, incidents, stream

# Create database tables at startup
Base.metadata.create_all(bind=engine)
ensure_sqlite_schema()

app = FastAPI(
    title="IncidentOps AI Backend",
    description="Autonomous Tier-3 Incident Response multi-agent backend running on LangGraph and Gemini.",
    version="1.0.0"
)

# Allow CORS for Next.js default local dev server port (3000) and general localhost usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(incidents.router, prefix="/api")
app.include_router(stream.router, prefix="/api")
app.include_router(config.router, prefix="/api")

@app.get("/")
def get_health_check():
    """Verify backend is healthy and running."""
    return {"status": "healthy", "service": "IncidentOps AI"}
