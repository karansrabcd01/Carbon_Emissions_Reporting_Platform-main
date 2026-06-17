from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import DATABASE_FILE, LEGACY_DATABASE_FILE, SessionLocal, create_tables
from .routers import analytics, emissions
from .utils import migrate_legacy_sqlite_data, seed_sample_data


app = FastAPI(
    title="Carbon Emissions Reporting Platform",
    description="Prototype GHG reporting platform for Scope 1 and Scope 2 reporting.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    create_tables()
    db = SessionLocal()
    try:
        seed_sample_data(db)
        migrate_legacy_sqlite_data(db, source_path=LEGACY_DATABASE_FILE, target_path=DATABASE_FILE)
    finally:
        db.close()


app.include_router(emissions.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {
        "message": "Carbon Emissions Reporting Platform API is running.",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database_file": str(DATABASE_FILE) if DATABASE_FILE else None,
        "database_exists": DATABASE_FILE.exists() if DATABASE_FILE else False,
    }
