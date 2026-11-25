"""Creation et execution d'un pipeline ETL de suivi des temps et couts."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ENTREE_DEFAUT = Path("data/saisies.csv")
SORTIE_DEFAUT = Path("output")


@dataclass(frozen=True)
class PipelineConfig:
    """Parametres de configuration du pipeline."""

    chemin_entree: Path = ENTREE_DEFAUT
    dossier_sortie: Path = SORTIE_DEFAUT
    majoration_charges: float = 1.15


def extraire(chemin: Path) -> pd.DataFrame:
    """Etape 1 : lit le fichier CSV brut."""
    return pd.read_csv(chemin)


def transformer(df: pd.DataFrame, majoration_charges: float = 1.15) -> pd.DataFrame:
    """Etape 2 : nettoie les donnees et calcule le cout charge."""
    propre = df.dropna(
        subset=["collaborateur", "projet", "heures", "taux_horaire"]
    ).copy()
    propre = propre[
        (propre["heures"] > 0) & (propre["taux_horaire"] > 0)
    ].copy()
    propre["collaborateur"] = (
        propre["collaborateur"].astype(str).str.strip().str.title()
    )
    propre["projet"] = propre["projet"].astype(str).str.strip().str.title()
    propre["cout_ht"] = (
        propre["heures"] * propre["taux_horaire"]
    ).round(2)
    propre["cout_charge"] = (
        propre["cout_ht"] * majoration_charges
    ).round(2)
    return propre.reset_index(drop=True)


def agreger_par_projet(df: pd.DataFrame) -> pd.DataFrame:
    """Etape 3a : agrege les heures et couts par projet."""
    if df.empty:
        return pd.DataFrame(
            columns=["projet", "heures", "cout_ht", "cout_charge"]
        )
    agreg = (
        df.groupby("projet", as_index=False)[
            ["heures", "cout_ht", "cout_charge"]
        ]
        .sum()
        .round(2)
    )
    return agreg.sort_values("cout_charge", ascending=False).reset_index(drop=True)


def agreger_par_collaborateur(df: pd.DataFrame) -> pd.DataFrame:
    """Etape 3b : agrege les heures et couts par collaborateur."""
    if df.empty:
        return pd.DataFrame(
            columns=["collaborateur", "heures", "cout_ht", "cout_charge"]
        )
    agreg = (
        df.groupby("collaborateur", as_index=False)[
            ["heures", "cout_ht", "cout_charge"]
        ]
        .sum()
        .round(2)
    )
    return agreg.sort_values("heures", ascending=False).reset_index(drop=True)


def charger(df: pd.DataFrame, chemin: Path) -> Path:
    """Etape 4 : ecrit un DataFrame dans un fichier CSV."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(chemin, index=False)
    return chemin


def construire_et_executer_pipeline(config: PipelineConfig | None = None) -> dict:
    """Assemble et execute toutes les etapes du pipeline."""
    cfg = config or PipelineConfig()
    brut = extraire(cfg.chemin_entree)
    propre = transformer(brut, majoration_charges=cfg.majoration_charges)
    par_projet = agreger_par_projet(propre)
    par_collaborateur = agreger_par_collaborateur(propre)

    charger(propre, cfg.dossier_sortie / "saisies_nettoyees.csv")
    charger(par_projet, cfg.dossier_sortie / "synthese_projets.csv")
    charger(
        par_collaborateur,
        cfg.dossier_sortie / "synthese_collaborateurs.csv",
    )

    return {
        "lignes_brutes": len(brut),
        "lignes_valides": len(propre),
        "total_heures": (
            round(float(propre["heures"].sum()), 2)
            if not propre.empty
            else 0.0
        ),
        "total_cout_charge": (
            round(float(propre["cout_charge"].sum()), 2)
            if not propre.empty
            else 0.0
        ),
        "projets": par_projet.to_dict(orient="records"),
        "collaborateurs": par_collaborateur.to_dict(orient="records"),
    }


if __name__ == "__main__":
    resultat = construire_et_executer_pipeline()
    print(
        f"Brutes: {resultat['lignes_brutes']} | "
        f"Valides: {resultat['lignes_valides']} | "
        f"Heures: {resultat['total_heures']} | "
        f"Cout charge: {resultat['total_cout_charge']}"
    )
