# Timesheet Pipeline API

A FastAPI application and ETL pipeline for cleaning timesheet entries,
calculating loaded costs, and generating summaries by project and employee.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure organizational SSO

The application uses OpenID Connect (OIDC). The identity provider and its
organization-specific group names have not been supplied yet, so sign-in stays
closed until the required settings are provided.

1. Copy `.env.example` to `.env`.
2. Ask your identity administrator for the OIDC issuer URL, client ID, client
   secret, and the exact group claim and group values.
3. Register `http://localhost:8000/auth/callback` as an allowed redirect URI
   for local development. Use the public HTTPS callback URL in production.
4. Set `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`,
   `OIDC_REDIRECT_URI`, `PUBLIC_BASE_URL`, `OIDC_GROUPS_CLAIM`, and the
   `OIDC_GROUP_*` values in `.env`.
5. Generate a session key, for example with `openssl rand -hex 32`, and set it
   as `SESSION_SECRET`.

Never commit `.env` or paste client secrets into chat. Production requires a
session secret, complete OIDC and role-group configuration, and HTTPS.

The current dashboard contains organization-wide cost data and is therefore
restricted to users mapped to the Finance role. Employee and team-scoped
manager views require the corresponding data model and authorization work;
those roles cannot access the current reports.

## Run locally

```bash
python -m src.pipeline
uvicorn src.api:app --env-file .env --reload --port 8000
```

Without OIDC settings, the application redirects protected pages to an English
configuration screen and rejects data API requests.

For a local UI preview only, explicitly enable the development demo account
and bind the server to loopback. The dashboard then opens directly:

```bash
APP_ENV=development DEV_AUTH_ENABLED=true uvicorn src.api:app --host 127.0.0.1 --port 8000
```

This local demo account is not organizational SSO and must never be enabled in
production. It is restricted to loopback connections; production startup
rejects `DEV_AUTH_ENABLED=true`.

Web interface:

- Dashboard: `http://localhost:8000/`
- Project report: `http://localhost:8000/reports/projects`
- Collaborator report: `http://localhost:8000/reports/collaborators`

API endpoints:

- `GET /health`
- `POST /pipeline/run`
- `GET /rapports/projets`
- `GET /rapports/collaborateurs`
- Interactive API documentation: `http://localhost:8000/docs`

## Code quality and tests

```bash
ruff check .
pytest -v
```

## Docker

```bash
docker build -t timesheet-pipeline-api .
docker run --rm --env-file .env -p 8000:8000 timesheet-pipeline-api
```

## CI/CD

The workflow in [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml):

1. installs Python 3.12;
2. runs Ruff;
3. runs pytest;
4. executes the pipeline;
5. uploads the generated CSV files as an artifact;
6. builds the Docker image;
7. publishes the image to Docker Hub on pushes to `main`.

Add the `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets in GitHub Actions to
enable image publishing.

## Planning documents

The following documents describe a proposal to review before extending the
application:

- [PRD.md](PRD.md) — product requirements, scope, and acceptance criteria;
- [ARCHITECTURE.md](ARCHITECTURE.md) — system design, data model, and technology
  choices;
- [TESTING.md](TESTING.md) — testing strategy;
- [DEVOPS.md](DEVOPS.md) — environments, CI/CD, and operations;
- [ROADMAP.md](ROADMAP.md) — phases, dependencies, and completion criteria.
