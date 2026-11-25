# Timesheet Pipeline API

A FastAPI application and ETL pipeline for cleaning timesheet entries,
calculating loaded costs, and generating summaries by project and employee.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

```bash
python -m src.pipeline
uvicorn src.api:app --reload --port 8000
```

Available endpoints:

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
docker run --rm -p 8000:8000 timesheet-pipeline-api
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
