from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.errors import AppError
from app.api import campaigns, streams, offers

app = FastAPI(title="Adrobot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code,
                        content={"error": type(exc).__name__, "detail": exc.detail})


app.include_router(campaigns.router)
app.include_router(streams.router)
app.include_router(offers.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
