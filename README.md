# Timesheet Pipeline API

Application FastAPI et pipeline ETL pour nettoyer les saisies de temps,
calculer les couts charges et produire des syntheses par projet et collaborateur.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Utilisation locale

```bash
python -m src.pipeline
uvicorn src.api:app --reload --port 8000
```

Endpoints disponibles :

- `GET /health`
- `POST /pipeline/run`
- `GET /rapports/projets`
- `GET /rapports/collaborateurs`
- Documentation interactive : `http://localhost:8000/docs`

## Qualite et tests

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

Le workflow [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml) :

1. installe Python 3.12 ;
2. execute Ruff ;
3. execute pytest ;
4. execute le pipeline ;
5. publie les CSV comme artefact ;
6. construit l'image Docker ;
7. sur un push vers `main`, publie l'image sur Docker Hub.

Ajouter dans GitHub Actions les secrets `DOCKERHUB_USERNAME` et
`DOCKERHUB_TOKEN` pour activer la publication.