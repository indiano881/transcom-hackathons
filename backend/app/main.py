import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette import status

from .database import init_db
from .exception import ClientErrorException, ServerErrorException
from .models import ApiErrorResponse
from .services.cleanup import cleanup_loop
from .routers import auth, upload, deployments


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

def conf_logger():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s.%(msecs)03d - %(levelname)s - %(threadName)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)

conf_logger()
app = FastAPI(title="Innovation Airlock", version="1.0.0", lifespan=lifespan)

@app.exception_handler(ClientErrorException)
async def client_error_exception_handler(req: Request, e: ClientErrorException):
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ApiErrorResponse(code=e.code, message=e.message).model_dump())

@app.exception_handler(ServerErrorException)
async def client_error_exception_handler(req: Request, e: ServerErrorException):
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=ApiErrorResponse(code=e.code, message=e.message).model_dump())

@app.exception_handler(Exception)
async def server_exception_handler(req: Request, e: Exception):
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=ApiErrorResponse(code='InternalServerError', message='Internal server error. Please try again later.').model_dump())

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, e: RequestValidationError):
    first_error = e.errors()[0] if e.errors() else {}
    field = first_error.get("loc", ["unknown"])[-1]

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ApiErrorResponse(code="IllegalArgument",message=f"{field} is invalid").model_dump())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(deployments.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "innovation-airlock"}
