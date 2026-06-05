# CaseLens

CaseLens is an MVP for Korean precedent search and comparison.

Current feedback-MVP dataset:

- 1,076 Korean precedent rows
- 119,542 paragraph rows
- 9,267 embeddings
- Primary domains covered: damages, labor, unjust enrichment, lease, tax, property, inheritance, family, contract, insurance, IP, and general civil/legal cases

The product is ready for feedback-MVP use, with a required notice that results are reference material and not legal advice.

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

Useful verification commands:

```powershell
npm.cmd run api:test
npm.cmd run web:lint
npm.cmd run web:build
npm.cmd run eval:mvp
```

Docker is not currently available on PATH in this workspace. When Docker is installed, PostgreSQL can be started with:

```powershell
docker compose -f infra\docker-compose.yml up -d postgres
```

## Environment

Copy `.env.example` to `.env` and set at least:

```text
DATABASE_URL=
LAW_API_OC=
SEARCH_API_URL=
NEXT_PUBLIC_APP_URL=
```

Embeddings default to the local sentence-transformers provider:

```text
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=dragonkue/multilingual-e5-small-ko
EMBEDDING_DIMENSION=768
```

`GEMINI_API_KEY` is optional. Without it, grounded local fallback summaries are used.

## Feedback MVP Search Scope

Current search works best for:

- damages and tort cases, including traffic accidents, negligence, comparative fault, consolation money, user liability, joint torts, limitation periods, and damages scope
- labor cases around wages, severance pay, worker status, dismissal, and employment-related disputes
- unjust enrichment and restitution disputes
- lease deposit return, building delivery, and related lease/property disputes
- tax cases around acquisition tax, tax assessments, cancellation suits, and correction requests
- property and registration disputes such as ownership transfer and cancellation registration
- inheritance and forced-heirship disputes
- family cases such as divorce, consolation money, and property division
- contract/payment/default disputes
- insurance, subrogation, and reimbursement disputes

Current thin areas:

- insurance-specific coverage is still small despite good compare metrics
- contract, family, inheritance, IP, and general domains need more cases for broad public usage
- criminal, administrative law outside tax, corporate/commercial, and IP are not full-scope search areas yet

## Feedback Labels To Watch

After release, monitor these labels first:

- `facts_not_similar`: if over 30%, tune material-fact extraction/ranking
- `wrong_statute`: if over 15%, inspect citation extraction and normalization
- `summary_error`: if over 15%, tune grounded summary fallback or Gemini prompt
- `not_relevant`: if over 25%, tune natural-search intent and ranking

## Release Gate

Before opening to users, run:

```powershell
npm.cmd run api:test
npm.cmd run web:lint
npm.cmd run web:build
npm.cmd run eval:mvp
```

Latest passing snapshot:

```text
api:test 53 passed
web:lint passed
web:build passed
statute precision@10 1.0
natural avg Top-5 relevant count 3.625
compare avg material fact match 0.836
compare avg domain match score 1.0
compare avg issue tag overlap 0.778
primary quality issue rate 0.061
primary missing scope rate 0.180
```
