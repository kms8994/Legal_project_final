# CaseLens

CaseLens is an MVP for Korean precedent search and comparison, focused first on damages cases.

## Structure

```text
apps/web          Next.js frontend and BFF
apps/search-api   FastAPI search and comparison API
db/migrations     PostgreSQL and pgvector migrations
infra             Local infrastructure
pipelines         Data collection and processing pipeline
docs              Product and engineering specs
```

## Local Commands

```powershell
npm.cmd --workspace apps/web run dev
```

FastAPI uses the local virtual environment under `apps/search-api/.venv`:

```powershell
npm.cmd run api:dev
```

Docker is not currently available on PATH in this workspace. When Docker is installed, PostgreSQL can be started with:

```powershell
docker compose -f infra\docker-compose.yml up -d postgres
```
