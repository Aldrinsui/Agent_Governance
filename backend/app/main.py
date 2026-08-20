from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import agents, profiles, events, findings, audit, demo

# For this take-home, tables are created directly at startup for simplicity.
# Alembic migrations are included (see alembic/) and are the intended path
# for anything beyond local/demo use -- see README "Running Locally".
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FLYYY.AI Agent Governance",
    description="Define, monitor, detect, and respond to AI agent behavior deviations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(profiles.router)
app.include_router(events.router)
app.include_router(findings.router)
app.include_router(audit.router)
app.include_router(demo.router)


@app.get("/health")
def health():
    return {"status": "ok"}
