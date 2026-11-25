"""Web application and API for the timesheet pipeline."""

import logging
import os
from pathlib import Path
import secrets
from typing import Any
from urllib.parse import urlparse

import pandas as pd
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from src.pipeline import (
    agreger_par_collaborateur,
    agreger_par_projet,
    construire_et_executer_pipeline,
    extraire,
    transformer,
)

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
APP_ENV = os.getenv("APP_ENV", "development").lower()
IS_PRODUCTION = APP_ENV in {"production", "prod"}
SESSION_SECRET = os.getenv("SESSION_SECRET")
DEV_AUTH_ENABLED = os.getenv("DEV_AUTH_ENABLED", "").lower() in {
    "1",
    "true",
    "yes",
}

if IS_PRODUCTION and not SESSION_SECRET:
    raise RuntimeError("SESSION_SECRET must be set in production.")
if IS_PRODUCTION and SESSION_SECRET and len(SESSION_SECRET) < 32:
    raise RuntimeError("SESSION_SECRET must be at least 32 characters.")
if IS_PRODUCTION and DEV_AUTH_ENABLED:
    raise RuntimeError("Development authentication cannot be enabled in production.")
if not SESSION_SECRET:
    SESSION_SECRET = secrets.token_urlsafe(32)
    logger.warning(
        "SESSION_SECRET is unset; using an ephemeral development key."
    )
if DEV_AUTH_ENABLED and not IS_PRODUCTION:
    logger.warning(
        "Development demo authentication is enabled; do not expose this server."
    )

app = FastAPI(
    title="Timesheet Pipeline API",
    description="Timesheet reporting and ETL pipeline.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def _missing_oidc_settings() -> list[str]:
    required = (
        "OIDC_ISSUER_URL",
        "OIDC_CLIENT_ID",
        "OIDC_CLIENT_SECRET",
        "OIDC_GROUP_EMPLOYEE",
        "OIDC_GROUP_MANAGER",
        "OIDC_GROUP_FINANCE",
    )
    missing = [name for name in required if not os.getenv(name)]
    redirect_uri = os.getenv("OIDC_REDIRECT_URI", "")
    if IS_PRODUCTION and not redirect_uri:
        missing.append("OIDC_REDIRECT_URI")
    elif IS_PRODUCTION and urlparse(redirect_uri).scheme != "https":
        missing.append("OIDC_REDIRECT_URI (must use HTTPS in production)")
    public_base_url = os.getenv("PUBLIC_BASE_URL", "")
    if IS_PRODUCTION and not public_base_url:
        missing.append("PUBLIC_BASE_URL")
    elif IS_PRODUCTION and urlparse(public_base_url).scheme != "https":
        missing.append("PUBLIC_BASE_URL (must use HTTPS in production)")
    issuer = os.getenv("OIDC_ISSUER_URL", "")
    if IS_PRODUCTION and issuer and urlparse(issuer).scheme != "https":
        missing.append("OIDC_ISSUER_URL (must use HTTPS in production)")
    return missing


if IS_PRODUCTION:
    startup_configuration_errors = _missing_oidc_settings()
    if startup_configuration_errors:
        raise RuntimeError(
            "OIDC configuration is incomplete: "
            + ", ".join(startup_configuration_errors)
        )


def _oidc_client() -> Any | None:
    if _missing_oidc_settings():
        return None

    issuer = os.environ["OIDC_ISSUER_URL"].rstrip("/")
    oauth = OAuth()
    return oauth.register(
        name="organization",
        server_metadata_url=f"{issuer}/.well-known/openid-configuration",
        client_id=os.environ["OIDC_CLIENT_ID"],
        client_secret=os.environ["OIDC_CLIENT_SECRET"],
        client_kwargs={"scope": "openid profile email"},
    )


def _roles_from_profile(profile: dict[str, Any]) -> list[str]:
    claim_name = os.getenv("OIDC_GROUPS_CLAIM", "groups")
    groups = profile.get(claim_name, [])
    if isinstance(groups, str):
        groups = [groups]
    if not isinstance(groups, (list, tuple, set)):
        return []

    group_roles = {
        os.getenv("OIDC_GROUP_EMPLOYEE"): "employee",
        os.getenv("OIDC_GROUP_MANAGER"): "manager",
        os.getenv("OIDC_GROUP_FINANCE"): "finance",
    }
    return sorted({
        role
        for group, role in group_roles.items()
        if group and group in groups
    })


def _is_same_origin_request(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return False

    configured_base = os.getenv("PUBLIC_BASE_URL")
    if configured_base:
        parsed_base = urlparse(configured_base)
        expected_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
    else:
        expected_origin = f"{request.url.scheme}://{request.url.netloc}"
    return origin.rstrip("/") == expected_origin.rstrip("/")


def _auth_page(
    request: Request,
    *,
    title: str,
    message: str,
    status_code: int = 200,
    missing_settings: list[str] | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="auth.html",
        context={
            "title": title,
            "message": message,
            "status_code": status_code,
            "missing_settings": missing_settings or [],
            "dev_auth_enabled": (
                DEV_AUTH_ENABLED and not IS_PRODUCTION
            ),
        },
        status_code=status_code,
    )


def _development_demo_user() -> dict[str, Any]:
    return {
        "sub": "local-development-demo",
        "name": "Development Demo User",
        "email": "",
        "roles": ["finance"],
        "auth_mode": "development_demo",
    }


_PUBLIC_PATHS = {
    "/health",
    "/auth/login",
    "/auth/callback",
    "/auth/logout",
    "/auth/dev-login",
}


@app.middleware("http")
async def require_sso(request: Request, call_next: Any) -> Response:
    """Protect application data and routes behind configured OIDC SSO."""
    path = request.url.path
    if path in _PUBLIC_PATHS or path.startswith("/static/"):
        return await call_next(request)

    missing_settings = _missing_oidc_settings()
    user = request.session.get("user")
    is_dev_session = (
        isinstance(user, dict)
        and user.get("auth_mode") == "development_demo"
        and DEV_AUTH_ENABLED
        and not IS_PRODUCTION
    )
    if missing_settings and DEV_AUTH_ENABLED and not IS_PRODUCTION:
        if not is_dev_session:
            user = _development_demo_user()
            request.session.clear()
            request.session["user"] = user
        request.state.current_user = user
        return await call_next(request)

    if missing_settings and not is_dev_session:
        if path.startswith(("/pipeline", "/rapports")):
            return JSONResponse(
                status_code=503,
                content={"detail": "Single sign-on is not configured."},
            )
        return RedirectResponse(url="/auth/login", status_code=303)

    if not isinstance(user, dict):
        if path.startswith(("/pipeline", "/rapports")):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required."},
            )
        return RedirectResponse(url="/auth/login", status_code=303)

    if "finance" not in user.get("roles", []):
        return _auth_page(
            request,
            title="Access not available",
            message=(
                "This reporting interface contains organization-wide cost "
                "data and is currently restricted to the Finance role. "
                "Employee and team-scoped views are not available yet."
            ),
            status_code=403,
        )

    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if not _is_same_origin_request(request):
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin request rejected."},
            )

    request.state.current_user = user
    return await call_next(request)


app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=IS_PRODUCTION,
    max_age=3600,
)


@app.get("/auth/login", response_class=HTMLResponse, include_in_schema=False)
async def auth_login(request: Request) -> Response:
    """Start the organization's OpenID Connect authorization flow."""
    missing_settings = _missing_oidc_settings()
    client = _oidc_client()
    if missing_settings or client is None:
        return _auth_page(
            request,
            title="Single sign-on is not configured",
            message=(
                "Ask your IT administrator to configure the organization's "
                "OpenID Connect issuer, client credentials, and role groups."
            ),
            status_code=503,
            missing_settings=missing_settings,
        )

    redirect_uri = os.getenv("OIDC_REDIRECT_URI")
    if not redirect_uri:
        redirect_uri = str(request.url_for("auth_callback"))
    return await client.authorize_redirect(request, redirect_uri)


@app.get("/auth/dev-login", include_in_schema=False)
async def auth_dev_login(request: Request) -> RedirectResponse:
    """Create a demo session when explicitly enabled outside production."""
    if not DEV_AUTH_ENABLED or IS_PRODUCTION:
        raise HTTPException(status_code=404, detail="Not found.")

    request.session.clear()
    request.session["user"] = _development_demo_user()
    return RedirectResponse(url="/", status_code=303)


@app.get(
    "/auth/callback",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def auth_callback(request: Request) -> Response:
    """Validate the OIDC response and create a minimal application session."""
    client = _oidc_client()
    if client is None:
        return _auth_page(
            request,
            title="Single sign-on is not configured",
            message="The OpenID Connect configuration is incomplete.",
            status_code=503,
            missing_settings=_missing_oidc_settings(),
        )

    token = await client.authorize_access_token(request)
    profile = token.get("userinfo")
    if not isinstance(profile, dict) or not profile.get("sub"):
        return _auth_page(
            request,
            title="Sign-in failed",
            message="The identity provider did not return a valid user profile.",
            status_code=401,
        )

    roles = _roles_from_profile(profile)
    if not roles:
        return _auth_page(
            request,
            title="No application role assigned",
            message=(
                "Your organization account is not assigned to a Timesheet "
                "Pipeline role. Contact your administrator."
            ),
            status_code=403,
        )

    request.session.clear()
    request.session["user"] = {
        "sub": str(profile["sub"]),
        "name": str(profile.get("name") or profile.get("email") or "User"),
        "email": str(profile.get("email") or ""),
        "roles": roles,
    }
    return RedirectResponse(url="/", status_code=303)


@app.get("/auth/logout", response_class=HTMLResponse, include_in_schema=False)
async def auth_logout(request: Request) -> HTMLResponse:
    """Clear the local session; the organization SSO session remains active."""
    request.session.clear()
    return _auth_page(
        request,
        title="You are signed out",
        message=(
            "Your Timesheet Pipeline session has ended. To end your "
            "organization session, sign out from your identity provider."
        ),
    )


def _charger_donnees() -> tuple[int, pd.DataFrame]:
    chemin = Path(os.getenv("INPUT_CSV", "data/saisies.csv"))
    brut = extraire(chemin)
    return len(brut), transformer(brut)


def _formater_nombre(value: int | float) -> str:
    return (
        f"{value:,.2f}"
        .replace(",", " ")
        .replace(".", ",")
        .replace(" ", "\u202f")
    )


def _report_csv(dataframe: pd.DataFrame, filename: str) -> Response:
    safe_dataframe = dataframe.copy()
    for column in safe_dataframe.select_dtypes(include=["object"]).columns:
        safe_dataframe[column] = safe_dataframe[column].map(
            lambda value: (
                f"'{value}"
                if isinstance(value, str)
                and value.lstrip().startswith(("=", "+", "-", "@"))
                else value
            )
        )
    return Response(
        content=safe_dataframe.to_csv(index=False),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def accueil(request: Request) -> HTMLResponse:
    """Display the timesheet dashboard."""
    lignes_brutes, propre = _charger_donnees()
    projets = agreger_par_projet(propre).to_dict(orient="records")
    collaborateurs = agreger_par_collaborateur(propre).to_dict(
        orient="records"
    )

    total_cout_charge = (
        float(propre["cout_charge"].sum()) if not propre.empty else 0.0
    )
    for projet in projets:
        projet["part"] = (
            round(float(projet["cout_charge"]) / total_cout_charge * 100)
            if total_cout_charge
            else 0
        )
    qualite_donnees = (
        round(len(propre) / lignes_brutes * 100) if lignes_brutes else 0
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_page": "dashboard",
            "current_user": request.state.current_user,
            "environment_label": APP_ENV.upper(),
            "lignes_brutes": lignes_brutes,
            "lignes_valides": len(propre),
            "lignes_exclues": lignes_brutes - len(propre),
            "qualite_donnees": qualite_donnees,
            "total_heures": (
                float(propre["heures"].sum()) if not propre.empty else 0.0
            ),
            "total_cout_charge": total_cout_charge,
            "nombre_projets": len(projets),
            "nombre_collaborateurs": len(collaborateurs),
            "projets": projets[:5],
            "run_succeeded": request.query_params.get("run") == "success",
            "format_number": _formater_nombre,
        },
    )


@app.get(
    "/reports/projects",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def page_rapport_projets(request: Request) -> HTMLResponse:
    """Display the project hours and costs report."""
    _, propre = _charger_donnees()
    return templates.TemplateResponse(
        request=request,
        name="report.html",
        context={
            "active_page": "projects",
            "current_user": request.state.current_user,
            "environment_label": APP_ENV.upper(),
            "report_title": "Project report",
            "report_description": "Hours and loaded costs grouped by project.",
            "report_type": "projects",
            "rows": agreger_par_projet(propre).to_dict(orient="records"),
            "download_url": "/reports/projects.csv",
            "format_number": _formater_nombre,
        },
    )


@app.get(
    "/reports/collaborators",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def page_rapport_collaborateurs(request: Request) -> HTMLResponse:
    """Display the hours and costs report by employee."""
    _, propre = _charger_donnees()
    return templates.TemplateResponse(
        request=request,
        name="report.html",
        context={
            "active_page": "collaborators",
            "current_user": request.state.current_user,
            "environment_label": APP_ENV.upper(),
            "report_title": "Employee report",
            "report_description": "Hours and loaded costs grouped by employee.",
            "report_type": "collaborators",
            "rows": agreger_par_collaborateur(propre).to_dict(
                orient="records"
            ),
            "download_url": "/reports/collaborators.csv",
            "format_number": _formater_nombre,
        },
    )


@app.get("/reports/projects.csv", include_in_schema=False)
def exporter_rapport_projets() -> Response:
    """Download the project report as CSV."""
    _, propre = _charger_donnees()
    return _report_csv(
        agreger_par_projet(propre),
        "synthese_projets.csv",
    )


@app.get("/reports/collaborators.csv", include_in_schema=False)
def exporter_rapport_collaborateurs() -> Response:
    """Download the employee report as CSV."""
    _, propre = _charger_donnees()
    return _report_csv(
        agreger_par_collaborateur(propre),
        "synthese_collaborateurs.csv",
    )


@app.post("/ui/pipeline/run", include_in_schema=False)
def lancer_pipeline_depuis_interface() -> RedirectResponse:
    """Run the pipeline from the interface and return to the dashboard."""
    construire_et_executer_pipeline()
    return RedirectResponse(url="/?run=success", status_code=303)


@app.get("/health")
def health() -> dict:
    """Report application liveness for infrastructure probes."""
    return {"status": "ok", "port": int(os.getenv("PORT", "8000"))}


@app.post("/pipeline/run")
def lancer_pipeline() -> dict:
    """Run the pipeline and generate CSV files in output/."""
    return construire_et_executer_pipeline()


@app.get("/rapports/projets")
def rapport_projets() -> list[dict]:
    """Return the project summary as JSON."""
    _, propre = _charger_donnees()
    return agreger_par_projet(propre).to_dict(orient="records")


@app.get("/rapports/collaborateurs")
def rapport_collaborateurs() -> list[dict]:
    """Return the employee summary as JSON."""
    _, propre = _charger_donnees()
    return agreger_par_collaborateur(propre).to_dict(orient="records")
