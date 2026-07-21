from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

from app.config import settings
from app.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks: initialize DB, start scheduler, start background collectors
    yield
    # Shutdown tasks: stop scheduler, close DB connections, etc.

app = FastAPI(
    title="GLM Usage Monitor",
    description="Z.ai Account-Wide GLM-5.2 Usage Monitoring Service",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
