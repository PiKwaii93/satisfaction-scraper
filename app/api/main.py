from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.database import ensure_product_schema
from app.api.routes.analysis_runs import router as analysis_runs_router
from app.api.routes.auth import router as auth_router
from app.api.routes.model_training import router as model_training_router

API_DESCRIPTION = """
API produit pour lancer, suivre et consulter des analyses d'avis clients depuis Trustpilot ou CSV.

Les endpoints metier sont proteges par un token JWT transmis dans le header
`Authorization: Bearer <token>`. L'endpoint `/health` reste public pour les sondes de disponibilite.
"""

OPENAPI_TAGS = [
    {
        "name": "system",
        "description": "Endpoints techniques publics, utiles pour verifier la disponibilite.",
    },
    {
        "name": "auth",
        "description": "Connexion JWT et consultation de l'utilisateur courant.",
    },
    {
        "name": "analysis-runs",
        "description": "Creation, suivi, consultation et export des analyses client.",
    },
    {
        "name": "model-training",
        "description": "Pilotage du reentrainement du modele de sentiment.",
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

app.include_router(auth_router)
app.include_router(analysis_runs_router)
app.include_router(model_training_router)


@app.get(
    "/health",
    tags=["system"],
    summary="Verifier la disponibilite de l'API",
)
def health_check():
    return {"status": "ok"}
