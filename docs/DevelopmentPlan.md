# CaseLens 개발 계획서

## 1. 현재 결정 상태

이 문서는 CaseLens MVP 구현 중 진행 상태를 확인하는 기준 문서다. 구현 중에는 이 문서의 체크리스트를 갱신하면서 진행한다.

### 확정된 결정

| 항목 | 결정 |
|------|------|
| MVP 도메인 | 손해배상 중심 |
| 초기 데이터 규모 | 300~500건 |
| 사용자 | 익명 사용자만 지원 |
| 데이터 소스 | 법령정보센터 API |
| API 사용 방식 | 런타임 백엔드 호출 금지, 로컬/배치 파이프라인에서 DB 적재용으로만 사용 |
| 런타임 검색 | 내부 PostgreSQL DB만 조회 |
| Frontend | Next.js + TypeScript |
| BFF | Next.js API Routes |
| Search API | FastAPI |
| DB | PostgreSQL 16 + pgvector |
| Pipeline | Python CLI, 이후 cron 또는 scheduler |
| RAG | 검색용, 비교용, 생성용으로 분리 |
| 비교 추천 원칙 | 사실관계/material facts 유사도 최우선, 결과 차이는 낮은 가중치 |
| 임베딩 MVP 기본값 | DB `vector(768)` 유지, 무료 로컬 `dragonkue/multilingual-e5-small-ko` 사용, 384차원 출력은 768차원으로 padding |
| 임베딩 모델 비교 | MVP 구현 이후 Korean local model, `bge-m3`, API embedding 후보를 평가 세트로 비교 |
| 외부 LLM 전송 원칙 | 사용자 자연어 사건 설명은 외부 LLM에 보내지 않고 검색 구조화/DB retrieval에만 사용 |
| 과금/로그인 | MVP 제외 |
| 관리자 UI | MVP 제외, review_status 기반 수동 검수 |

### 아직 최종 확정이 필요한 항목

| 항목 | 현재 상태 | 다음 행동 |
|------|-----------|----------|
| 최종 조문 15~30개 | P0 조문별 판례 수 확인 완료 | P1 확장 여부와 최종 15~30개 조문 확정 |
| 법령정보센터 API 응답 구조 | pagination 확인, `collect_laws`/`collect_cases` 구현 및 dry-run 검증 완료 | Supabase DB 기준으로 upsert 실검증 |
| UI 와이어프레임 | 작성 완료 | Next.js 화면 구현 시 기준으로 사용 |
| API 계약/fixture | 작성 완료 | FastAPI schema와 mock fixture 작성 시 기준으로 사용 |
| 관리자 검수 운영 | 최소 상태값만 정의 | `AdminReviewSpec.md` 작성 |
| 실제 평가 gold set | 초안만 있음 | 수집 후 판례 ID 기반 라벨링 |

### 지금 다음에 해야 할 일

1. Supabase PostgreSQL에 적용된 migration과 샘플 seed 상태를 기준으로 조문 검색 흐름을 확장한다.
2. `collect_laws`, `collect_cases`, `normalize`, `split`, `extract`, `structure`, `validate`를 DB upsert 모드로 순서대로 실검증한다.
3. 조문 검색 화면 다음 단계로 판례 상세 API 또는 자연어 intent parser를 구현한다.
4. 이후 embed 파이프라인과 비교 후보 API를 붙인다.

### 다음 작업자용 실행 요약

이 섹션만 읽어도 다음 단계로 바로 들어갈 수 있게 현재 상태와 실행 명령을 고정한다.

현재 완료된 범위:

```text
문서 확정
→ 법령정보센터 API 샘플 검증
→ pagination 확인
→ collect_laws / collect_cases 설계 확정
→ Next.js + FastAPI + Docker Compose 부트스트랩
→ FastAPI /health 구현
→ Next.js 첫 검색 화면 초안 구현
→ 핵심 DB schema migration 작성
→ 샘플 seed SQL 작성
→ collect_laws 구현 및 dry-run 검증
→ collect_cases 구현 및 dry-run 검증
→ normalize/split 파이프라인 구현 및 unit test 검증
→ extract 파이프라인 구현 및 unit test 검증
→ validate 파이프라인 구현 및 unit test 검증
→ rule fallback structure 파이프라인 구현 및 unit test 검증
→ Supabase PostgreSQL + pgvector migration 적용
→ 정상 한글 샘플 seed Supabase 적재
→ 조문 검색 API 실DB smoke test
→ Next.js BFF와 검색 결과 화면 구현
```

현재 주요 파일:

| 목적 | 파일 |
|------|------|
| 다음 작업 기준 | `docs/DevelopmentPlan.md` |
| UI 기준 | `docs/Wireframes.md`, `docs/UIUXSpec.md`, `docs/FrontendSpec.md` |
| API 계약 | `docs/APIContract.md`, `docs/BackendSpec.md` |
| 수집 설계 | `docs/DataCollectionRunbook.md`, `docs/StatuteScope.md` |
| DB 기준 | `docs/DatabaseSpec.md`, `db/migrations/001_extensions.sql`, `db/migrations/002_core_schema.sql` |
| seed 기준 | `db/seeds/001_sample_cases.sql` |
| 수집 파이프라인 | `pipelines/collect_laws.py`, `pipelines/collect_cases.py` |
| 처리 파이프라인 | `pipelines/normalize.py`, `pipelines/split.py`, `pipelines/extract.py`, `pipelines/structure.py`, `pipelines/validate.py` |
| 파이프라인 공용 로직 | `pipelines/common/env.py`, `pipelines/common/law_api.py`, `pipelines/common/text.py`, `pipelines/common/extract.py`, `pipelines/common/structure.py`, `pipelines/common/validate.py` |
| 파이프라인 테스트 | `apps/search-api/tests/test_pipeline_text.py`, `apps/search-api/tests/test_pipeline_extract.py`, `apps/search-api/tests/test_pipeline_structure.py`, `apps/search-api/tests/test_pipeline_validate.py` |
| 웹 앱 | `apps/web/src/app/page.tsx` |
| 검색 API | `apps/search-api/app/main.py`, `apps/search-api/app/api/health.py` |
| 로컬 인프라 | `infra/docker-compose.yml` |

검증 완료:

```powershell
npm.cmd --workspace apps/web run lint
npm.cmd --workspace apps/web run build
npm.cmd run api:test
npm.cmd run collect:laws -- --dry-run
npm.cmd run collect:cases -- --limit 1 --display 1 --max-pages 1 --dry-run
apps\search-api\.venv\Scripts\python.exe -m compileall pipelines
```

검증 결과:

```text
Next.js lint 통과
Next.js production build 통과
FastAPI /health TestClient 테스트 통과
파이프라인 unit test 포함 `npm.cmd run api:test` 14개 통과
`collect_laws --dry-run` P0 조문 6개 매핑 통과
`collect_cases --dry-run` 판례 목록→상세 1건 매핑 통과
`compileall pipelines` 통과
웹 dev server 임시 실행 후 http://localhost:3000 HTTP 200 및 CaseLens 렌더링 확인
uvicorn foreground startup 확인
조문 정규화 서비스, 내부 DB repository, `POST /api/v1/search/statute` 라우터 구현 및 fake repository 기반 API 계약 테스트 통과
Supabase DB `pgcrypto`, `vector` extension 적용 확인
Supabase DB 핵심 테이블과 샘플 seed 적재 확인
`민법 제750조` 조문 검색 API 실DB smoke test 200 응답 및 샘플 판례 3건 반환 확인
Next.js `/api/search/statute` BFF route 구현 및 localhost:3000 HTTP 200 확인
```

현재 구현된 실행 스크립트:

```powershell
npm.cmd run web:dev
npm.cmd run web:build
npm.cmd run web:lint
npm.cmd run api:dev
npm.cmd run api:test
npm.cmd run api:health
npm.cmd run collect:laws
npm.cmd run collect:cases
npm.cmd run pipeline:normalize
npm.cmd run pipeline:split
npm.cmd run pipeline:extract
npm.cmd run pipeline:structure
npm.cmd run pipeline:validate
```

dry-run 또는 소량 검증 예시:

```powershell
npm.cmd run collect:laws -- --dry-run
npm.cmd run collect:cases -- --limit 1 --display 1 --max-pages 1 --dry-run
npm.cmd run pipeline:normalize -- --dry-run-text "<p>【주 문】 원고의 청구를 일부 인용한다.</p>"
npm.cmd run pipeline:split -- --dry-run-text "【주 문】 원고의 청구를 일부 인용한다. 【이 유】 1. 기초사실 원고는 사고로 상해를 입었다."
npm.cmd run pipeline:extract -- --dry-run-text "피고는 민법 제750조에 따라 손해배상책임을 부담한다. 원고의 청구를 일부 인용한다."
npm.cmd run pipeline:structure -- --dry-run-text "【주 문】 일부 인용한다. 【이 유】 피고는 민법 제750조에 따른 책임이 있다."
npm.cmd run pipeline:validate -- --dry-run-json "{""cited_articles"":[{""normalized_ref"":""민법_제750조""}],""outcome"":{""disposition"":""일부 인용"",""direction"":""원고 일부 유리""},""facets"":{""legal_domain"":""손해배상""},""evidence_spans"":{""cited_articles"":[{""char_start"":0,""char_end"":8}],""outcome"":{""char_start"":20,""char_end"":25}},""confidence_score"":0.75}" --known-articles "민법_제750조" --text-length 40
```

현재 막힌 점:

```text
docker 명령이 PATH에 없어 PostgreSQL 16 컨테이너 실행과 pgvector extension 실검증은 아직 못 했다.
따라서 C 체크리스트의 PostgreSQL 16 실행, pgvector extension 활성화는 미완료다.
```

다음에 바로 실행할 순서:

```powershell
# 1. Docker 사용 가능 여부 확인
docker --version

# 2. DB 실행
docker compose -f infra\docker-compose.yml up -d postgres

# 3. migration 적용
docker exec -i caselens-postgres psql -U caselens -d caselens < db\migrations\001_extensions.sql
docker exec -i caselens-postgres psql -U caselens -d caselens < db\migrations\002_core_schema.sql

# 4. seed 적용
docker exec -i caselens-postgres psql -U caselens -d caselens < db\seeds\001_sample_cases.sql

# 5. extension과 table 생성 확인
docker exec -it caselens-postgres psql -U caselens -d caselens -c "\dx"
docker exec -it caselens-postgres psql -U caselens -d caselens -c "\dt"

# 6. pipeline DB upsert 실검증, 처음에는 limit를 작게 둔다
npm.cmd run collect:laws
npm.cmd run collect:cases -- --limit 3 --display 3 --max-pages 1
npm.cmd run pipeline:normalize -- --limit 3
npm.cmd run pipeline:split -- --limit 3 --overwrite
npm.cmd run pipeline:extract -- --limit 3
npm.cmd run pipeline:structure -- --limit 3 --overwrite
npm.cmd run pipeline:validate -- --limit 3

# 7. 웹/API 검증
npm.cmd --workspace apps/web run build
npm.cmd run api:test

# 8. 조문 검색 API 실DB smoke test
npm.cmd run api:dev
# 별도 터미널에서 실행
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/search/statute" -ContentType "application/json" -Body "{""query"":""민법 제750조"",""page"":1,""size"":20,""sort"":""relevance""}"
```

로컬 Docker는 선택 사항이다. 현재 MVP 검증 DB는 Supabase PostgreSQL을 기준으로 진행한다.

다음 구현 단위:

```text
1. `pipeline:embed`를 OpenAI provider로 소량 실행해 Supabase `case_embeddings` 적재를 검증한다.
2. 자연어 검색/비교 후보의 embedding score 품질을 샘플 쿼리로 점검한다.
3. 조문 검색 precision@10, 자연어 검색 Top-5 관련 판례 수, 비교 후보 material fact match를 기록한다.
4. 익명 세션/검색 로그/비교 로그는 MVP 핵심 흐름 이후 운영·평가 단계에서 붙인다.
```

### 최근 진행 상황

| 날짜 | 진행 내용 | 상태 |
|------|-----------|------|
| 2026-06-03 | git 저장소 초기화 | 완료 |
| 2026-06-03 | `.env`, `.env.example`, `.gitignore` 작성 | 완료 |
| 2026-06-03 | `DataCollectionRunbook.md` 작성 | 완료 |
| 2026-06-03 | 법령정보센터 API 샘플 호출 스크립트 작성 | 완료 |
| 2026-06-03 | 법령 목록/본문, 판례 목록/상세 샘플 호출 검증 | 완료 |
| 2026-06-03 | P0 조문별 판례 수 확인 및 응답 필드 DB 매핑 초안 작성 | 완료 |
| 2026-06-03 | `Wireframes.md`, `APIContract.md` 작성 | 완료 |
| 2026-06-03 | 법령정보센터 API pagination 확인 및 collector 설계 확정 | 완료 |
| 2026-06-03 | Next.js/FastAPI/Docker Compose 프로젝트 부트스트랩 | 완료 |
| 2026-06-03 | 핵심 DB schema migration 작성 | 완료 |
| 2026-06-03 | `db/seeds/001_sample_cases.sql` 작성 | 완료 |
| 2026-06-03 | `pipelines.collect_laws` 구현 및 P0 조문 dry-run 검증 | 완료 |
| 2026-06-03 | `pipelines.collect_cases` 구현 및 판례 1건 dry-run 검증 | 완료 |
| 2026-06-03 | `pipelines.normalize`, `pipelines.split` 구현 및 텍스트 처리 unit test 작성 | 완료 |
| 2026-06-03 | `pipelines.extract` 구현 및 규칙 기반 조문/outcome 추출 unit test 작성 | 완료 |
| 2026-06-03 | `pipelines.validate` 구현 및 review_status/confidence 검증 unit test 작성 | 완료 |
| 2026-06-04 | `pipelines.structure` rule fallback 구현 및 material_facts unit test 작성 | 완료 |
| 2026-06-04 | Docker 부재 재확인 후 fallback으로 조문 정규화 서비스와 `POST /api/v1/search/statute` 구현 | 완료 |
| 2026-06-04 | SQLAlchemy `psycopg` v3 URL 보정 및 조문 검색 API fake repository 테스트 작성, `api:test` 14개 통과 | 완료 |
| 2026-06-04 | Supabase PostgreSQL 연결, pgvector extension/core schema 적용, 정상 한글 seed 3건 적재 | 완료 |
| 2026-06-04 | Next.js BFF `/api/search/statute`와 조문 검색 결과 화면 구현, lint/build/API test 통과 | 완료 |
| 2026-06-04 | Supabase 기준 `collect_laws`, `collect_cases`, `normalize`, `split`, `extract`, `structure`, `validate` limit=3 DB upsert 실검증 | 완료 |
| 2026-06-04 | 범위 밖 인용 조문 정책 반영: `민법 제399조`, `민법 제766조`를 P0 수집 범위에 추가하고 unknown article은 invalid 대신 needs_review 처리 | 완료 |
| 2026-06-04 | 추가 조문 수집 후 validate 재실행: 6건 중 6건 auto_validated, invalid 0건 확인 | 완료 |
| 2026-06-04 | 판례 상세 API/화면과 비교 후보 API/화면 구현, structured fallback Set B 랭킹 및 테스트 추가 | 완료 |
| 2026-06-04 | `POST /api/v1/compare` 비교 분석 API와 `/compare?base=&target=` 화면 구현, structured fallback 분석/근거 링크 테스트 추가 | 완료 |
| 2026-06-04 | `POST /api/v1/feedback` 피드백 API와 비교 분석 화면 피드백 UI 구현, label 검증/저장 테스트 추가 | 완료 |
| 2026-06-04 | 자연어 intent parser와 `POST /api/v1/search/natural` structured fallback 검색 API/화면 탭 구현, parsed intent 패널 추가 | 완료 |
| 2026-06-04 | deterministic local fallback `pipeline:embed` 구현, facts/issue/material_facts/combined/paragraph embedding 생성 및 자연어 검색·비교 후보 랭킹에 embedding score 연결 | 완료 |
| 2026-06-04 | DB `vector(768)` 유지 결정, OpenAI `text-embedding-3-small` dimensions=768 provider 추가, API 키 없을 때 local fallback 유지 | 완료 |
| 2026-06-04 | OpenAI 결제 제약으로 무료 로컬 `dragonkue/multilingual-e5-small-ko` provider 전환, sentence-transformers 설치 및 dry-run 임베딩 생성 확인 | 완료 |
| 2026-06-04 | 검색 결과 카드에 `evidence_ids`뿐 아니라 실제 근거 문단 `evidence_snippets`를 포함하도록 API/UI 연결 | 완료 |
| 2026-06-04 | `GET /api/v1/cases/{case_id}/rag-summary` 근거 제한 요약 API와 판례 상세 화면 Grounded summary 섹션 구현 | 완료 |
| 2026-06-04 | `GEMINI_API_KEY`가 있으면 Gemini `generateContent`로 판례 RAG 요약을 생성하고, 키 없음/실패 시 로컬 grounded 요약으로 fallback하도록 구현 | 완료 |
| 2026-06-04 | 사용자 자연어 사건 설명은 외부 LLM에 보내지 않고, 외부 생성 모델에는 공개 판례의 구조화 필드와 선택된 evidence 문단만 보내는 정책 확정 | 완료 |

## 2. 개발 원칙

- 코드는 작게 시작하되 데이터는 많이 넣을 수 있게 설계한다.
- MVP에서는 검색과 비교 흐름을 먼저 완성하고, 고급 운영 도구는 뒤로 미룬다.
- 파이프라인은 모든 단계가 재실행 가능해야 한다.
- RAG는 검색, 비교, 생성 단계로 분리한다.
- 비교 추천은 사실관계 유사도를 최우선으로 둔다.
- 구현 중 판단이 흔들리면 `PRD.md`와 `RAGAndRankingSpec.md`를 우선 기준으로 삼는다.
- 법령정보센터 API는 런타임 백엔드가 아니라 로컬/배치 파이프라인에서만 호출한다.
- 사용자 자연어 사건 설명은 개인 정보와 민감 맥락이 포함될 수 있으므로 외부 LLM에 전송하지 않는다.
- 사용자 입력은 intent parsing, 키워드 추출, 로컬 임베딩, DB retrieval까지만 사용한다.
- Gemini 등 외부 생성 모델에는 DB에 저장된 공개 판례의 구조화 필드와 선택된 evidence 문단만 전송한다.
- 판례 원문 전체는 외부 생성 모델에 보내지 않고, Top-K evidence snippets만 보낸다.

## 3. 추천 폴더 구조

```text
caselens/
  apps/
    web/
      app/
      components/
      lib/
      api/
      package.json
    search-api/
      app/
        api/
        core/
        schemas/
        services/
        db/
      tests/
      pyproject.toml
  packages/
    prompts/
    shared-types/
  pipelines/
    collect/
    normalize/
    split/
    extract/
    structure/
    validate/
    embed/
    load/
  db/
    migrations/
    seeds/
  docs/
  infra/
    docker-compose.yml
  scripts/
  .env.example
  README.md
```

## 4. Phase 0: 프로젝트 부트스트랩

목표: 로컬에서 웹, API, DB가 함께 실행되는 골격을 만든다.

작업:

- monorepo 디렉터리 생성
- Next.js + TypeScript 앱 생성
- FastAPI 앱 생성
- PostgreSQL 16 + pgvector Docker Compose 구성
- `.env.example` 작성
- `GET /health` 작성
- DB migration 실행 명령 준비

완료 기준:

- `web` 첫 화면이 열린다.
- `search-api`의 `/health`가 200을 반환한다.
- PostgreSQL에 접속 가능하다.
- pgvector extension이 활성화된다.

## 5. Phase 1: DB 스키마와 샘플 데이터

목표: 판례 원문, 문단, 구조화 결과, 임베딩, 검색 로그를 저장할 수 있다.

작업:

- `cases`
- `case_paragraphs`
- `case_structures`
- `case_embeddings`
- `laws`
- `law_aliases`
- `articles`
- `search_queries`
- `comparison_feedbacks`
- `llm_runs`
- `pipeline_runs`
- `prompt_versions`

완료 기준:

- 샘플 판례 20건을 수동 seed로 넣을 수 있다.
- 판례 원문과 문단이 연결된다.
- 조문 alias 조회가 가능하다.
- 임베딩 테이블에 vector(768)이 저장된다.

## 6. Phase 2: 데이터 파이프라인 MVP

목표: 손해배상 도메인 판례 300~500건을 수집하고 검색 가능한 구조로 만든다.

작업:

- 핵심 조문 목록 확정
- 법령정보센터 API 수집 테스트
- `collect_laws`로 법령/조문 DB 적재
- `collect_cases`로 판례 목록 수집
- 판례 상세 원문 수집
- 중복 제거
- HTML 제거
- 문단/섹션 분리
- 규칙 기반 조문 추출
- LLM 구조화
- material_facts 추출
- evidence span 연결
- confidence 계산
- needs_review 분류

완료 기준:

- 최소 300건 이상 저장
- 중복률 3% 이하
- 구조화 confidence 0.7 이상 판례 70% 이상
- LLM 실패/검증 실패 데이터가 버려지지 않고 재처리 대상이 된다.

## 7. Phase 3: RAG 검색 API

목표: 조문 검색과 자연어 검색 결과를 판례 카드로 제공한다.

작업:

- 조문 정규화 API
- 조문 검색 API
- 자연어 intent parser
- hybrid retrieval
- RRF 또는 weighted ranking
- evidence paragraph retrieval
- 판례 카드 요약 생성
- LLM 실패 시 구조화 요약 fallback

완료 기준:

- `POST /api/v1/search/statute` 동작
- `POST /api/v1/search/natural` 동작
- 런타임 검색 중 법령정보센터 API를 호출하지 않는다.
- 결과 카드에 요약, 조문, outcome, 근거 링크가 포함된다.
- 검색 p95 2.5초 이하를 목표로 측정 가능하다.

## 8. Phase 4: 비교 추천 API

목표: 기준 판례와 논리적으로 사실관계가 유사한 비교 후보를 추천한다.

작업:

- 기준 판례 상세 조회
- 후보 1차 검색
- material facts 정밀 재랭킹
- 결과 차이 필터/표시
- 비교 후보 Top 5 응답
- 추천 이유 생성

완료 기준:

- 기준 판례 선택 후 후보 Top 5가 표시된다.
- 후보는 fact similarity와 material fact match를 우선으로 정렬된다.
- outcome difference는 표시되지만 점수 중심이 아니다.
- 후보마다 `추천 이유`, `공통 사실`, `차이 가능성`이 제공된다.

## 9. Phase 5: 비교 화면과 RAG 생성

목표: 두 판례의 공통점, 미세 차이, 결과 차이를 근거 문단과 함께 표시한다.

작업:

- 비교 대상 두 판례의 facts/issue/reasoning/outcome 문단 retrieval
- 비교 분석 프롬프트 작성
- evidence id 기반 생성
- turning points 추출
- LLM timeout fallback
- 피드백 저장 UI

완료 기준:

- 두 판례 비교 화면이 표시된다.
- 공통 사실과 차이점마다 evidence id가 있다.
- 결과 차이는 단정이 아니라 판례 구조화 결과와 원문 근거 기반으로 표시된다.
- LLM 실패 시 표 기반 비교가 표시된다.

## 10. Phase 6: UI/UX 정리

목표: 학습자가 검색에서 비교까지 자연스럽게 이동할 수 있다.

작업:

- 검색 시작 화면
- 검색 결과 화면
- 기준 판례 선택 상태
- 비교 후보 화면
- 판례 비교 화면
- 판례 상세 화면
- 피드백 UI
- 예외 UX
- 모바일 비교 화면

완료 기준:

- 검색 시작에서 비교 결과까지 3클릭 이내
- 사용자가 현재 단계와 다음 행동을 이해할 수 있다.
- AI 요약에는 원문 확인 필요 배지가 있다.
- 결과 없음, 후보 부족, LLM 실패 상태가 자연스럽게 처리된다.

## 11. Phase 7: 평가와 QA

목표: 기능 동작뿐 아니라 검색 품질을 측정한다.

작업:

- 조문 검색 평가 세트 10개
- 자연어 검색 평가 세트 20개
- 비교 후보 평가 세트 10쌍
- 구조화 검증 세트 30건
- RAG chunk 전략 검증
- 임베딩 모델 후보 비교
- 비교 후보 랭킹 가중치 비교
- API integration test
- 프론트 E2E test

완료 기준:

- 평가 스크립트가 실행된다.
- 주요 지표가 문서화된다.
- 목표 미달 지표가 있으면 원인이 기록된다.
- MVP 기본값인 768차원 단일 임베딩 모델로 end-to-end가 동작한다.
- 구현 완료 후 `ko-sbert`, `bge-m3`, API embedding 후보를 같은 gold set으로 비교할 수 있다.
- 비교 랭킹 가중치 Set A/B/C 중 MVP 기본값을 선택한 근거가 기록된다.

### Phase 7에서 수행할 RAG/임베딩 검증

RAG와 임베딩 모델 검증은 실제 DB, 검색 API, 비교 API가 구현된 뒤 수행한다. 문서 단계에서 모델을 최종 확정하지 않고, MVP 기본값으로 먼저 구현한 뒤 평가 세트로 교체 여부를 판단한다.

검증 후보:

```text
1. Korean lightweight local model
2. OpenAI text-embedding-3-small, dimensions=768
3. bge-m3
```

chunk 전략 후보:

```text
facts only
facts + issue
material_facts only
combined
paragraph-level
```

비교 지표:

```text
Recall@5
MRR@10
nDCG@10
Top-5 material fact match 평균
Top-5 outcome difference 포함 수
검색 latency
임베딩 생성 비용
```

랭킹 가중치 실험:

```text
Set A: 벡터 중심
Set B: 균형형
Set C: material facts 중심
```

MVP 구현 기본값은 `Set B: 균형형`으로 두고, 평가 결과에 따라 조정한다.

## 12. Phase 8: 운영 준비

목표: 데이터 추가, 재처리, 장애 대응이 가능하다.

작업:

- pipeline run 로그 확인 화면 또는 CLI
- 재수집 정책
- 재구조화 정책
- 재임베딩 정책
- 비용 추적
- rate limit
- 개인정보/검색 로그 보존 기간 문서화

완료 기준:

- 새 조문을 추가해도 파이프라인을 다시 실행할 수 있다.
- 모델 또는 프롬프트 변경 시 영향 범위를 찾을 수 있다.
- 실패 데이터를 재처리할 수 있다.

## 13. 구현 순서 요약

```text
문서 확정
→ 법령정보센터 API 수집 테스트 [완료]
→ DataCollectionRunbook 작성 [완료]
→ UI 와이어프레임 작성 [완료]
→ API 계약/fixture 작성 [완료]
→ pagination 확인 [완료]
→ collect_laws/collect_cases 설계 확정 [완료]
→ 프로젝트 부트스트랩 [완료]
→ DB migration 작성 [완료]
→ PostgreSQL/pgvector 실행 확인 [완료: Supabase]
→ 샘플 데이터 seed SQL 작성 [완료]
→ 샘플 데이터 seed 실적재 [완료: Supabase]
→ 법령/조문 수집 파이프라인 [완료]
→ 판례 수집 파이프라인 [완료]
→ normalize/split 파이프라인 [완료]
→ extract 파이프라인 [완료]
→ validate 파이프라인 [완료]
→ 구조화 파이프라인 [완료: rule fallback]
→ 임베딩
→ 조문 검색 API [완료]
→ 자연어 검색 API
→ 비교 후보 API
→ 비교 분석 API
→ 프론트 검색 화면 [완료: 조문 검색]
→ 프론트 비교 화면
→ 평가 세트
→ QA와 운영 준비
```

## 14. 전체 진행 체크리스트

이 체크리스트는 구현 중 계속 갱신한다. `[x]`는 완료, `[ ]`는 미완료다.

### A. 문서와 의사결정

- [x] PRD 작성
- [x] 개발 계획서 작성
- [x] 아키텍처 문서 작성
- [x] 백엔드 명세 작성
- [x] 프론트엔드 명세 작성
- [x] DB 명세 작성
- [x] 데이터 파이프라인 명세 작성
- [x] RAG/랭킹 명세 작성
- [x] UI/UX 명세 작성
- [x] 법률/개인정보 정책 작성
- [x] MVP 익명 사용자 정책 확정
- [x] 법령정보센터 API는 로컬/배치 수집 전용으로 확정
- [x] RAG/임베딩 모델 비교는 코드 구현 이후 평가 단계로 확정
- [x] `DataCollectionRunbook.md` 작성
- [x] `Wireframes.md` 작성
- [x] `APIContract.md` 작성
- [ ] `AdminReviewSpec.md` 작성

### B. 법령정보센터 API와 데이터 수집 검증

- [x] 법령정보센터 API 키 준비
- [x] 법령 조회 샘플 호출
- [x] 조문 조회 샘플 호출
- [x] 판례 목록 샘플 호출
- [x] 판례 상세 샘플 호출
- [x] pagination 방식 확인
- [ ] rate limit 또는 호출 제한 확인
- [x] 응답 인코딩/HTML 구조 확인
- [x] P0 조문별 수집 가능 판례 수 확인
- [x] API 응답을 DB 테이블 필드에 매핑
- [x] `collect_laws` 설계 확정
- [x] `collect_cases` 설계 확정

### C. 프로젝트 부트스트랩

- [x] monorepo 생성
- [x] Next.js 앱 생성
- [x] FastAPI 앱 생성
- [x] Docker Compose 작성
- [ ] PostgreSQL 16 실행
- [ ] pgvector extension 활성화
- [x] Supabase PostgreSQL 연결
- [x] Supabase pgvector extension 활성화
- [x] `.env.example` 작성
- [x] FastAPI `/health` 구현
- [x] Next.js 첫 화면 구현
- [x] 웹 lint/build 검증
- [x] FastAPI `/health` 테스트 검증

### D. DB와 마이그레이션

- [x] `laws` 테이블
- [x] `law_aliases` 테이블
- [x] `articles` 테이블
- [x] `cases` 테이블
- [x] `case_paragraphs` 테이블
- [x] `case_structures` 테이블
- [x] `case_embeddings` 테이블
- [x] `search_queries` 테이블
- [x] `comparison_feedbacks` 테이블
- [x] `llm_runs` 테이블
- [x] `pipeline_runs` 테이블
- [x] `prompt_versions` 테이블
- [x] GIN 인덱스 생성
- [x] pgvector 인덱스 생성
- [x] 샘플 seed SQL 작성
- [x] 샘플 seed 데이터 적재

### E. 데이터 파이프라인

- [x] `collect_laws` 구현
- [x] `collect_cases` 구현
- [x] normalize 구현
- [x] split 구현
- [x] extract 구현
- [x] validate 구현
- [x] structure 구현
- [x] `collect_laws` Supabase DB upsert 실검증
- [x] `collect_cases` Supabase DB upsert 실검증
- [x] normalize Supabase DB 갱신 실검증
- [x] split Supabase DB upsert 실검증
- [x] extract Supabase DB upsert 실검증
- [x] structure Supabase DB upsert 실검증
- [x] validate Supabase DB 갱신 실검증
- [x] 범위 밖 인용 조문 needs_review 정책 적용
- [x] `민법 제399조`, `민법 제766조` P0 수집 범위 추가
- [x] embed 구현
- [ ] load/index 구현
- [ ] source_hash 중복 제거
- [x] evidence span 생성
- [x] confidence 계산
- [x] needs_review 분류
- [ ] 실패 데이터 재처리 가능

### F. 백엔드 API

- [x] 조문 정규화 서비스
- [x] 내부 DB 기반 조문 검증
- [x] 조문 검색 API
- [x] 조문 검색 API 실DB smoke test
- [x] 자연어 intent parser
- [x] 자연어 검색 API
- [x] evidence retrieval
- [x] 판례 상세 API
- [x] 비교 후보 API
- [x] 비교 분석 API
- [x] 피드백 API
- [ ] LLM timeout fallback
- [ ] 공통 에러 코드
- [ ] 런타임 외부 법령 API 호출 없음 확인

### G. RAG와 랭킹

- [x] facts embedding 생성
- [x] issue embedding 생성
- [x] material_facts embedding 생성
- [x] combined embedding 생성
- [x] paragraph evidence embedding 생성
- [ ] 조문 검색 가중치 적용
- [x] 자연어 검색 가중치 적용
- [x] 비교 후보 Set B 기본 가중치 적용
- [x] outcome difference 낮은 가중치 유지
- [ ] 결과 차이보다 사실관계 유사도 우선 검증
- [ ] LLM 생성 결과 evidence id 검증
- [x] 판례 상세 근거 제한 요약 API

### H. 프론트엔드와 UI/UX

- [x] 검색 시작 화면
- [x] 검색 모드 탭
- [x] 검색 결과 카드
- [x] 자연어 parsed intent 패널
- [ ] 기준 판례 선택
- [x] 비교 후보 화면
- [x] 비교 후보 추천 이유 표시
- [x] 판례 비교 매트릭스
- [x] 원문 근거 문단 표시
- [x] 판례 상세 화면
- [x] 피드백 UI
- [ ] 면책 고지 표시
- [ ] 모바일 비교 화면
- [ ] 결과 없음/후보 부족/LLM 실패 예외 UI

### I. 익명 사용자와 사용량 제한

- [ ] anonymous_session_id 생성
- [ ] 익명 세션 쿠키 또는 localStorage 정책 확정
- [ ] 검색 로그 저장
- [ ] 비교 로그 저장
- [x] 피드백 저장
- [ ] 검색 rate limit
- [ ] 비교 분석 rate limit
- [ ] 검색 로그 90일 보존 정책 반영

보류 메모: anonymous_session_id, 검색 로그, 비교 로그, 로그 보존 정책은 기능 품질 개선과 운영 분석에 필요하지만, 현재 MVP 핵심 사용자 흐름은 이미 `검색 → 판례 상세 → 비교 후보 → 비교 분석 → 피드백`까지 연결되어 있다. 따라서 이 항목들은 자연어 검색/임베딩 기반 검색을 붙인 뒤 운영·평가 단계에서 구현한다.

### J. 평가와 QA

- [ ] 조문 검색 평가 세트 10개
- [ ] 자연어 검색 평가 세트 20개
- [ ] 비교 후보 평가 세트 10쌍
- [ ] 구조화 검증 세트 30건
- [ ] Backend unit test
- [ ] Backend integration test
- [ ] Pipeline test
- [ ] Frontend E2E test
- [ ] RAG chunk 전략 비교
- [ ] 임베딩 모델 후보 비교
- [ ] 랭킹 가중치 Set A/B/C 비교
- [ ] 품질 지표 기록

### K. 운영 준비

- [ ] pipeline_runs 확인 CLI
- [ ] llm_runs 비용 추적
- [ ] 재수집 절차
- [ ] 재구조화 절차
- [ ] 재임베딩 절차
- [ ] needs_review 수동 검수 절차
- [ ] 데이터 기준일 UI 표시
- [ ] 법률 고지 최종 확인

## 15. 단계별 테스트 체크리스트

### 구현 전 테스트

- [x] 법령정보센터 API에서 P0 조문을 조회할 수 있는가
- [x] 판례 목록과 상세 원문을 가져올 수 있는가
- [x] API 응답을 내부 DB schema에 매핑할 수 있는가
- [ ] 약칭 조문 입력을 내부 DB로 정규화할 수 있는가

### 백엔드 구현 후 테스트

- [x] FastAPI가 외부 법령 API 없이 검색하는가
- [x] 조문 검색 결과가 cited_articles 기준으로 나온다
- [x] 자연어 검색 결과가 evidence 문단을 포함한다
- [x] 비교 후보가 사실관계 유사도 중심으로 정렬된다
- [x] LLM 실패 시 fallback이 나온다

### 프론트 구현 후 테스트

- [x] 검색 시작에서 비교 결과까지 이동 가능하다
- [ ] 기준 판례 선택 상태가 유지된다
- [x] 비교 후보 추천 이유가 보인다
- [ ] 모바일에서 비교 화면이 깨지지 않는다
- [x] 피드백을 제출할 수 있다

### MVP 완료 전 테스트

- [ ] 검색 p95 latency 측정
- [ ] 조문 검색 precision@10 측정
- [ ] 자연어 검색 Top-5 관련 판례 수 측정
- [ ] 비교 후보 Top-5 fact/material match 측정
- [ ] evidence span 연결률 측정
- [ ] 법률 고지와 원문 링크 표시 확인

## 16. 다음 작업 우선순위

현재 문서 기준 다음 작업 순서는 아래가 가장 좋다.

1. 조문 검색 precision@10, 자연어 검색 Top-5 관련 판례 수, 비교 후보 material fact match를 기록한다.
2. 자연어 검색/비교 후보의 embedding score 품질을 샘플 쿼리로 점검한다.
3. needs_review 비율이 높은 원인을 확인하고 structure rule fallback을 보강한다.
4. 익명 세션/검색 로그/비교 로그는 운영·평가 단계로 보류한다.

## 17. 로컬 임베딩 적재 테스트와 판례 수집 우선순위

### 17.1 로컬 임베딩 적재 테스트 결과

- 2026-06-04 기준 OpenAI 유료 API 대신 무료 로컬 모델 `dragonkue/multilingual-e5-small-ko`를 사용한다.
- `sentence-transformers` 출력 384차원은 기존 DB 벡터 스키마 유지를 위해 768차원으로 padding한다.
- `limit 10` 테스트: 판례 단위 6건, 문단 10건, 총 28개 임베딩 upsert 성공.
- `limit 100` 테스트: 판례 단위 6건, 문단 100건, 총 118개 임베딩 upsert 성공.
- `limit 1000` 테스트: 현재 DB에 존재하는 문단이 459개라 문단 459건까지 전체 임베딩 upsert 완료.
- `pipeline_runs`에는 `stage=embed`, `status=succeeded`, `provider=sentence-transformers`, `model=dragonkue/multilingual-e5-small-ko`, `dimension=768`로 기록된다.

### 17.2 다음 판례 적재 우선순위

1. P0 손해배상 핵심 조문 인용 판례를 먼저 적재한다.
   - 민법 제750조: 불법행위 손해배상 일반
   - 민법 제751조: 위자료, 정신적 손해
   - 민법 제763조: 불법행위 손해배상 준용
   - 민법 제393조: 손해배상 범위
   - 민법 제396조: 과실상계
   - 민법 제399조: 손해배상자의 대위
   - 민법 제766조: 손해배상청구권 소멸시효
   - 자동차손해배상 보장법 제3조: 자동차 사고 손해배상 책임
2. 검색/비교 품질을 빨리 검증하기 위해 교통사고 손해배상 판례를 최우선으로 모은다.
   - 교통사고
   - 무단횡단
   - 전방주시의무
   - 과실상계
   - 운행자 책임
   - 자동차손해배상
3. 그 다음은 비교 후보 품질을 높이는 세부 유형을 확장한다.
   - 사용자책임
   - 공동불법행위
   - 감독자 책임
   - 손해배상 범위
   - 인과관계
   - 위자료
4. 사건종류는 MVP에서 `민사`를 우선한다.
5. 원문이 없거나 구조화가 어려운 판례, 손해배상 관련성이 약한 판례, outcome이 불명확한 판례는 저장하더라도 검색 노출 우선순위를 낮춘다.

### 17.3 다음 실행 순서

1. 적재 후 조문 검색 precision@10, 자연어 검색 Top-5 관련 판례 수, 비교 후보 material fact match를 측정한다.
2. needs_review 판례 샘플을 확인해 구조화 fallback 규칙을 보강한다.
3. 검색/비교 화면에서 샘플 쿼리 E2E smoke test를 진행한다.

### 17.4 300건 수집과 재처리 결과

- 2026-06-05 기준 `collect_cases --scope damages --priority P0 --limit 300 --display 100 --include-keywords` 실행 성공.
- 수집 결과: `queries_run=3`, `list_rows_seen=300`, `unique_case_ids=300`, `details_fetched=300`, `cases_upserted=300`, `failed_items=0`.
- 중복 판례가 `cases_case_no_decision_date_court_name_key` 제약에 걸려 수집이 중단되던 문제를 수정했다. 이제 `external_id`, `(case_no, decision_date, court_name)`, `source_hash` 기준 기존 row를 찾아 갱신한다.
- `pipeline:normalize -- --limit 300`: `input_count=220`, `normalized_count=220`.
- `pipeline:split -- --limit 50`: `input_count=50`, `cases_processed=50`, `paragraphs_upserted=7547`. 이후 동일 명령 재실행 시 `input_count=0`으로 문단 없는 판례가 더 없음을 확인했다.
- `pipeline:structure -- --limit 300`: `input_count=217`, `structures_upserted=217`, `needs_review=22`.
- `pipeline:validate -- --limit 300`: `input_count=226`, `auto_validated=52`, `needs_review=174`, `invalid=0`.
- `pipeline:embed -- --limit 300`: `case_inputs=220`, `paragraph_inputs=300`, `embeddings_upserted=1032`.
- `pipeline:split -- --limit 300 --overwrite`는 Supabase statement timeout에 걸렸다. 대량 overwrite는 작은 batch로 나누거나 timeout 설정을 별도로 조정한다.
