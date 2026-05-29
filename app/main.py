import app.config  # Load environment variables first
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import api_router
from app.utils.db import engine, Base

# Import all models to ensure they register on Base.metadata
import app.models  

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="Agentic Software Developer API",
    description="API for the Agentic Software Developer project",
    version="1.0.0",
    lifespan=lifespan
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "System is healthy"}
