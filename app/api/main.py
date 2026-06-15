from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.database import ensure_product_schema
from app.api.routes.analysis_runs import router as analysis_runs_router

API_DESCRIPTION = """
API produit pour lancer, suivre et consulter des analyses d'avis clients Trustpilot.

Les endpoints métier sont protégés par une clé API à transmettre dans le header
`X-API-Key`. L'endpoint `/health` reste public pour les sondes de disponibilité.
"""

OPENAPI_TAGS = [
    {
        "name": "system",
        "description": "Endpoints techniques publics, utiles pour vérifier la disponibilité.",
    },
    {
        "name": "analysis-runs",
        "description": "Création, suivi, consultation et export des analyses client.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_product_schema(max_attempts=30, delay_seconds=2)
    yield


app = FastAPI(
    title="Satisfaction Client API",
    description=API_DESCRIPTION,
    version="0.1.0",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://frontend:5173",
        "http://satisfaction_frontend:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis_runs_router)


@app.get(
    "/health",
    tags=["system"],
    summary="Vérifier la disponibilité de l'API",
)
def health_check():
    return {"status": "ok"}
