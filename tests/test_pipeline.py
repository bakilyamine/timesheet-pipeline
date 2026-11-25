"""Tests unitaires du pipeline et des endpoints de l'application."""

import pandas as pd
from fastapi.testclient import TestClient

from src.api import app
from src.pipeline import (
    PipelineConfig,
    agreger_par_collaborateur,
    agreger_par_projet,
    construire_et_executer_pipeline,
    transformer,
)

client = TestClient(app)


def _donnees_brutes() -> pd.DataFrame:
    return pd.DataFrame({
        "collaborateur": ["amine", "nadia", "ida", "luc"],
        "projet": [" alpha ", "ALPHA", "Beta", "Beta"],
        "heures": [4.0, 6.0, None, -2.0],
        "taux_horaire": [100.0, 50.0, 80.0, 80.0],
    })


def test_nettoyage_et_calcul_cout():
    propre = transformer(_donnees_brutes(), majoration_charges=1.10)
    assert len(propre) == 2
    assert propre["cout_ht"].sum() == 700.0
    assert propre["cout_charge"].sum() == 770.0


def test_agregations_projet_et_collaborateur():
    propre = transformer(_donnees_brutes(), majoration_charges=1.0)
    par_projet = agreger_par_projet(propre)
    par_collab = agreger_par_collaborateur(propre).set_index("collaborateur")

    assert par_projet.loc[0, "projet"] == "Alpha"
    assert par_projet.loc[0, "cout_charge"] == 700.0
    assert par_collab.loc["Amine", "heures"] == 4.0
    assert par_collab.loc["Nadia", "heures"] == 6.0


def test_pipeline_complet_et_exports(tmp_path):
    csv_in = tmp_path / "saisies.csv"
    csv_in.write_text(
        "collaborateur,projet,heures,taux_horaire\n"
        "Amine,Alpha,2.0,100.0\n"
        "Nadia,Beta,3.0,100.0\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "output"
    resume = construire_et_executer_pipeline(
        PipelineConfig(
            chemin_entree=csv_in,
            dossier_sortie=out_dir,
            majoration_charges=1.0,
        )
    )
    assert resume["lignes_valides"] == 2
    assert resume["total_cout_charge"] == 500.0
    assert (out_dir / "saisies_nettoyees.csv").exists()
    assert (out_dir / "synthese_projets.csv").exists()
    assert (out_dir / "synthese_collaborateurs.csv").exists()


def test_endpoints_application():
    r_accueil = client.get("/", follow_redirects=False)
    assert r_accueil.status_code == 307
    assert r_accueil.headers["location"] == "/docs"

    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    r_projets = client.get("/rapports/projets")
    assert r_projets.status_code == 200
    assert len(r_projets.json()) >= 1
