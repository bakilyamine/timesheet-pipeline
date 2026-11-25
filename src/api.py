"""Application web / API pilotant et exposant le pipeline de suivi."""

import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.pipeline import (
    agreger_par_collaborateur,
    agreger_par_projet,
    construire_et_executer_pipeline,
    extraire,
    transformer,
)

app = FastAPI(title="Timesheet Pipeline API", version="1.0.0")


@app.get("/", include_in_schema=False)
def accueil() -> RedirectResponse:
    """Redirige la page d'accueil vers la documentation interactive."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict:
    """Verifie la disponibilite de l'application."""
    return {"status": "ok", "port": int(os.getenv("PORT", "8000"))}


@app.post("/pipeline/run")
def lancer_pipeline() -> dict:
    """Execute le pipeline et genere les fichiers CSV dans output/."""
    return construire_et_executer_pipeline()


@app.get("/rapports/projets")
def rapport_projets() -> list[dict]:
    """Retourne la synthese par projet."""
    chemin = os.getenv("INPUT_CSV", "data/saisies.csv")
    propre = transformer(extraire(chemin))
    return agreger_par_projet(propre).to_dict(orient="records")


@app.get("/rapports/collaborateurs")
def rapport_collaborateurs() -> list[dict]:
    """Retourne la synthese par collaborateur."""
    chemin = os.getenv("INPUT_CSV", "data/saisies.csv")
    propre = transformer(extraire(chemin))
    return agreger_par_collaborateur(propre).to_dict(orient="records")
