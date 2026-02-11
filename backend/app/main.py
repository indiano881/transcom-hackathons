import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .database import init_db
from .services.cleanup import cleanup_loop
from .routers import upload, deployments
import sys
sys.path.insert(0, str(__file__.rsplit('/', 2)[0]))
from auth.routes import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Innovation Airlock", version="1.0.0", lifespan=lifespan)

# Add session middleware (must be added before CORS for proper cookie handling)
import os
secret_key = os.getenv("SESSION_SECRET_KEY", "your-secret-key-change-this-in-production")
app.add_middleware(SessionMiddleware, secret_key=secret_key)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(deployments.router, prefix="/api")
app.include_router(auth_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "innovation-airlock"}
