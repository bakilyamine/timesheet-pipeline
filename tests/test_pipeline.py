"""Tests unitaires du pipeline et des endpoints de l'application."""

import base64
import json

import pandas as pd
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner

import src.api as api
from src.pipeline import (
    PipelineConfig,
    agreger_par_collaborateur,
    agreger_par_projet,
    construire_et_executer_pipeline,
    transformer,
)

client = TestClient(api.app)


def _authenticated_client(
    monkeypatch,
    roles: list[str] | None = None,
) -> TestClient:
    settings = {
        "OIDC_ISSUER_URL": "https://idp.example.test",
        "OIDC_CLIENT_ID": "timesheet-test",
        "OIDC_CLIENT_SECRET": "test-client-secret",
        "OIDC_GROUP_EMPLOYEE": "timesheet-employees",
        "OIDC_GROUP_MANAGER": "timesheet-managers",
        "OIDC_GROUP_FINANCE": "timesheet-finance",
    }
    for key, value in settings.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://testserver")

    test_client = TestClient(api.app)
    session = {
        "user": {
            "sub": "finance-user",
            "name": "Finance User",
            "email": "finance@example.test",
            "roles": roles or ["finance"],
        }
    }
    payload = base64.b64encode(json.dumps(session).encode("utf-8"))
    signed_session = TimestampSigner(api.SESSION_SECRET).sign(payload)
    test_client.cookies.set("session", signed_session.decode("utf-8"))
    return test_client


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


def test_endpoints_application(monkeypatch):
    finance_client = _authenticated_client(monkeypatch)
    r_accueil = finance_client.get("/", follow_redirects=False)
    assert r_accueil.status_code == 200
    assert "text/html" in r_accueil.headers["content-type"]
    assert "Overview" in r_accueil.text
    assert 'href="/static/app.css?v=2"' in r_accueil.text
    assert 'src="/static/app.js?v=2"' in r_accueil.text
    assert "Import quality" in r_accueil.text
    assert "Accepted entries" in r_accueil.text

    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    r_projets = finance_client.get("/rapports/projets")
    assert r_projets.status_code == 200
    assert len(r_projets.json()) >= 1


def test_pages_rapport_et_exports(monkeypatch):
    finance_client = _authenticated_client(monkeypatch)
    page_projets = finance_client.get("/reports/projects")
    assert page_projets.status_code == 200
    assert "Project report" in page_projets.text
    assert "Treasury Portal" in page_projets.text

    page_collaborateurs = finance_client.get("/reports/collaborators")
    assert page_collaborateurs.status_code == 200
    assert "Employee report" in page_collaborateurs.text
    assert "Amine" in page_collaborateurs.text

    export = finance_client.get("/reports/projects.csv")
    assert export.status_code == 200
    assert "attachment; filename=\"synthese_projets.csv\"" in export.headers[
        "content-disposition"
    ]
    assert "projet,heures,cout_ht,cout_charge" in export.text


def test_lancement_pipeline_depuis_interface(monkeypatch):
    def fake_pipeline():
        return {"lignes_valides": 1}

    monkeypatch.setattr(api, "construire_et_executer_pipeline", fake_pipeline)
    finance_client = _authenticated_client(monkeypatch)
    response = finance_client.post(
        "/ui/pipeline/run",
        headers={"origin": "http://testserver"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/?run=success"


def test_ressources_frontend_et_export_csv_securise(monkeypatch):
    finance_client = _authenticated_client(monkeypatch)
    css = finance_client.get("/static/app.css")
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]

    donnees = pd.DataFrame({
        "projet": ["=HYPERLINK(\"https://example.test\")"],
        "heures": [1.0],
        "cout_ht": [10.0],
        "cout_charge": [11.5],
    })
    monkeypatch.setattr(api, "_charger_donnees", lambda: (1, donnees))
    export = finance_client.get("/reports/projects.csv")

    assert export.status_code == 200
    assert "'=HYPERLINK" in export.text


def test_sso_required_for_application_data(monkeypatch):
    for name in (
        "OIDC_ISSUER_URL",
        "OIDC_CLIENT_ID",
        "OIDC_CLIENT_SECRET",
        "OIDC_GROUP_EMPLOYEE",
        "OIDC_GROUP_MANAGER",
        "OIDC_GROUP_FINANCE",
    ):
        monkeypatch.delenv(name, raising=False)

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"

    login = client.get("/auth/login")
    assert login.status_code == 503
    assert "Single sign-on is not configured" in login.text
    assert "OIDC_ISSUER_URL" in login.text

    api_response = client.get("/rapports/projets")
    assert api_response.status_code == 503
    assert api_response.json()["detail"] == "Single sign-on is not configured."


def test_development_demo_login_is_explicit_and_local(monkeypatch):
    monkeypatch.setattr(api, "DEV_AUTH_ENABLED", True)
    for name in (
        "OIDC_ISSUER_URL",
        "OIDC_CLIENT_ID",
        "OIDC_CLIENT_SECRET",
        "OIDC_GROUP_EMPLOYEE",
        "OIDC_GROUP_MANAGER",
        "OIDC_GROUP_FINANCE",
    ):
        monkeypatch.delenv(name, raising=False)
    demo_client = TestClient(api.app)

    login_page = demo_client.get("/auth/login")
    assert login_page.status_code == 503
    assert "Development-only demo access is enabled" in login_page.text

    dashboard = demo_client.get("/")
    assert dashboard.status_code == 200
    assert "Development Demo User" in dashboard.text

    login = demo_client.get("/auth/dev-login", follow_redirects=False)
    assert login.status_code == 303


def test_non_finance_role_cannot_access_global_cost_dashboard(monkeypatch):
    employee_client = _authenticated_client(monkeypatch, ["employee"])

    response = employee_client.get("/")

    assert response.status_code == 403
    assert "restricted to the Finance role" in response.text


def test_mutating_requests_require_same_origin(monkeypatch):
    finance_client = _authenticated_client(monkeypatch)

    response = finance_client.post("/ui/pipeline/run", follow_redirects=False)

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-origin request rejected."


def test_oidc_groups_are_mapped_to_application_roles(monkeypatch):
    monkeypatch.setenv("OIDC_GROUPS_CLAIM", "memberOf")
    monkeypatch.setenv("OIDC_GROUP_EMPLOYEE", "timesheet-employees")
    monkeypatch.setenv("OIDC_GROUP_MANAGER", "timesheet-managers")
    monkeypatch.setenv("OIDC_GROUP_FINANCE", "timesheet-finance")

    roles = api._roles_from_profile({
        "memberOf": ["timesheet-employees", "timesheet-finance"]
    })

    assert roles == ["employee", "finance"]


def test_oidc_client_registers_configured_issuer(monkeypatch):
    _authenticated_client(monkeypatch)

    oidc_client = api._oidc_client()

    assert oidc_client is not None


def test_oidc_callback_creates_finance_session(monkeypatch):
    finance_client = _authenticated_client(monkeypatch, ["employee"])

    class FakeOIDCClient:
        async def authorize_access_token(self, request):
            return {
                "userinfo": {
                    "sub": "finance-subject",
                    "name": "Finance User",
                    "email": "finance@example.test",
                    "groups": ["timesheet-finance"],
                }
            }

    monkeypatch.setattr(api, "_oidc_client", lambda: FakeOIDCClient())
    response = finance_client.get(
        "/auth/callback?code=test-code&state=test-state",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    dashboard = finance_client.get("/")
    assert dashboard.status_code == 200
    assert "Finance User" in dashboard.text
