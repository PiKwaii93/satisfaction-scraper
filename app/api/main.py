from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.database import ensure_product_schema
from app.api.routes.analysis_runs import router as analysis_runs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_product_schema(max_attempts=30, delay_seconds=2)
    yield


app = FastAPI(
    title="Satisfaction Client API",
    description="API produit pour lancer et consulter des analyses d'avis clients.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis_runs_router)


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}
