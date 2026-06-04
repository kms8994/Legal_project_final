# CaseLens 새 프로젝트 착수 가이드

> 기준 문서: `D:\CaseLens_TechSpec_v03.md` v0.4  
> 목적: CaseLens를 기존 서비스 수정이 아니라 새 프로젝트로 시작할 때 필요한 결정사항, 초기 구조, 구현 순서, 산출물을 한 번에 확인하기 위한 실행 문서

---

## 1. 프로젝트 목표

CaseLens는 사용자가 법조문, 자연어 사건 설명, 사건번호를 입력하면 관련 판례를 찾고, 기준 판례와 비교 판례의 사실관계/쟁점/결과 차이를 교육적으로 확인할 수 있게 하는 판례 검색 및 비교 서비스다.

MVP의 핵심 가치는 다음 세 가지다.

1. 조문 기준 판례 검색
2. 자연어 기반 유사 판례 검색
3. 기준 판례와 "사실관계는 유사하지만 판단 결과나 분기점이 다른 판례" 비교

---

## 2. MVP 확정 아키텍처

새 프로젝트에서는 구현팀이 아키텍처 선택을 다시 반복하지 않도록 아래 구조를 기본값으로 확정한다.

| 영역 | MVP 선택 | 이유 |
|------|----------|------|
| Frontend | Next.js + TypeScript | 검색/비교 UI, 인증, BFF 구성에 적합 |
| BFF | Next.js API Routes | 사용자 인증, 요금제, rate limit, Search API 프록시 |
| Search API | FastAPI | 판례 검색, 임베딩, LLM, Python 파이프라인과 연결 용이 |
| DB | PostgreSQL 16 + pgvector | 메타데이터, 관계, 벡터 검색을 MVP에서 단일 DB로 처리 |
| 전문 검색 | MVP에서는 PostgreSQL 기반 검색 우선 | Elasticsearch는 초기 범위에서 제외 |
| Cache | MVP에서는 최소 캐시, 이후 Redis | 비용/복잡도 절감 |
| LLM | Claude Haiku/Sonnet 기준 | intent 파싱, 구조화, 비교 요약 |
| Pipeline | Python CLI + cron | Airflow는 운영 고도화 단계에서 도입 |
| Infra | local Docker Compose, production AWS ECS/RDS | MVP와 확장 모두 대응 가능 |

MVP에서 제외하는 것:

- Elasticsearch 클러스터
- Qdrant 분리 운영
- Airflow
- 대규모 관리자 시스템
- 민간 판례 DB 연동
- 실시간 법률 자문성 답변

---

## 3. 권장 새 프로젝트 폴더 구조

```text
caselens/
  apps/
    web/                         # Next.js frontend + BFF
      app/
      components/
      lib/
      api/
      package.json
    search-api/                  # FastAPI 검색/비교 API
      app/
        api/
        core/
        schemas/
        services/
        db/
      tests/
      pyproject.toml
  packages/
    shared-types/                # API 공통 타입, OpenAPI 생성 타입
    prompts/                     # LLM 프롬프트 버전 관리
  pipelines/
    collect/
    normalize/
    structure/
    embed/
    load/
  db/
    migrations/
    seeds/
  docs/
    TechSpec.md
    DataCollectionPlan.md
    EvaluationSet.md
    AdminReviewSpec.md
    PromptRegistry.md
    LegalPolicy.md
    TestStrategy.md
  infra/
    docker-compose.yml
    aws/
  scripts/
  .env.example
  README.md
```

---

## 4. 초기 산출물 체크리스트

새 프로젝트 첫 주차에는 코드를 많이 짜기보다 기반 결정을 문서와 스키마로 고정해야 한다.

| 산출물 | 위치 | 완료 기준 |
|--------|------|-----------|
| 기술 명세서 | `docs/TechSpec.md` | v0.4 내용을 새 레포 기준으로 이관 |
| 데이터 수집 계획 | `docs/DataCollectionPlan.md` | MVP 도메인, 핵심 조문 50~100개 확정 |
| DB 마이그레이션 | `db/migrations/001_init.sql` | 핵심 테이블과 pgvector 적용 |
| API 계약 | `apps/search-api/openapi.json` 또는 자동 생성 | `/search`, `/compare`, `/cases/:id` 정의 |
| 프롬프트 레지스트리 | `packages/prompts/` | intent, structure, compare 프롬프트 분리 |
| 평가 세트 초안 | `docs/EvaluationSet.md` | 조문 30개, 자연어 50개, 비교 30쌍 목표 |
| 법률/정책 문서 | `docs/LegalPolicy.md` | 면책 고지, 원문 표시 정책, 개인정보 항목 |
| 테스트 전략 | `docs/TestStrategy.md` | unit/integration/e2e/search-quality 구분 |

---

## 5. 구현 순서

### Phase 0. 프로젝트 부트스트랩

목표: 로컬에서 Next.js, FastAPI, PostgreSQL + pgvector가 함께 실행되는 기본 골격을 만든다.

작업:

- monorepo 생성
- Next.js 앱 생성
- FastAPI 앱 생성
- Docker Compose로 PostgreSQL + pgvector 구성
- `.env.example` 작성
- health check API 작성

완료 기준:

- `web`에서 첫 화면 표시
- `search-api`에서 `/health` 응답
- DB migration 실행 가능

### Phase 1. DB와 판례 수집 기반

목표: 판례 원문을 저장하고 구조화할 수 있는 최소 DB를 만든다.

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

완료 기준:

- 샘플 판례 100건 저장
- 문단 분리 완료
- 조문 alias 조회 가능

### Phase 2. 수집/정규화/구조화 파이프라인

목표: law.go.kr 기반 판례를 수집하고, 검색 가능한 구조화 데이터로 변환한다.

작업:

- 판례 목록 수집
- 판례 상세 원문 수집
- HTML 제거
- 문단/섹션 분리
- 규칙 기반 조문 추출
- 저신뢰 판례 LLM 구조화
- `evidence_spans` 연결
- `confidence_score` 계산

완료 기준:

- MVP 도메인별 최소 500건 수집
- 핵심 구조화 필드 confidence 0.7 이상 판례 70% 이상
- `needs_review` 판례 분류 가능

### Phase 3. 임베딩과 검색 API

목표: 조문 검색과 자연어 검색을 API로 제공한다.

작업:

- facts, issue, holding, distinction, combined 임베딩 텍스트 생성
- 임베딩 모델 1개로 고정
- pgvector 저장
- 조문 검색 API
- 자연어 intent parser
- 자연어 hybrid search
- 검색 결과 카드 스키마

완료 기준:

- 조문 검색 precision@10 0.8 이상
- 자연어 검색 Top-5 관련 판례 평균 3건 이상
- 검색 p95 latency 2.5초 이하

### Phase 4. 비교 API와 비교 UI

목표: 기준 판례와 비교 판례의 공통점/차이점/분기점을 보여준다.

작업:

- 기준 판례 선택 API
- 비교 후보 추천
- `comparison_candidate_score`
- `outcome_contrast_score`
- LLM 비교 요약
- evidence link 반환
- 나란히 비교 UI
- 피드백 제출 UI

완료 기준:

- 기준 판례 선택 후 비교 후보 Top-5 표시
- 유효 비교 후보 평균 2건 이상
- LLM timeout 시 기본 비교 fallback 표시

### Phase 5. 품질 평가와 운영 준비

목표: 배포 전 검색 품질과 운영 리스크를 점검한다.

작업:

- 평가 데이터셋 생성
- search-quality test 자동화
- LLM 비용 캐시
- rate limit
- 법률 고지 UI
- 개인정보 처리 항목 정리
- staging 배포

완료 기준:

- 품질 게이트 통과
- 필수 고지 문구 UI 반영
- 월 LLM 비용 상한 알림 설정
- staging QA 완료

---

## 6. 핵심 API 목록

| API | 역할 | MVP 포함 |
|-----|------|----------|
| `GET /health` | Search API 상태 확인 | 예 |
| `POST /api/v1/search/statute` | 조문 기반 판례 검색 | 예 |
| `POST /api/v1/search/natural` | 자연어 기반 판례 검색 | 예 |
| `GET /api/v1/cases/{case_id}` | 판례 상세 조회 | 예 |
| `POST /api/v1/compare/candidates` | 기준 판례 기반 비교 후보 추천 | 예 |
| `POST /api/v1/compare` | 두 판례 비교 분석 | 예 |
| `POST /api/v1/feedback` | 검색/비교 피드백 저장 | 예 |
| `POST /api/v1/admin/review` | 구조화 검수 반영 | Phase 2 이후 |

---

## 7. 필수 DB 테이블

새 프로젝트 시작 시 최소한 아래 테이블을 migration으로 만든다.

```text
cases
case_paragraphs
case_structures
case_embeddings
laws
law_aliases
articles
search_queries
comparison_feedbacks
llm_runs
prompt_versions
pipeline_runs
```

추가 고려 테이블:

```text
users
subscriptions
usage_limits
admin_review_tasks
case_clusters
```

---

## 8. 환경 변수

```env
# Database
DATABASE_URL=postgresql://...

# Law data
LAW_API_KEY=...

# LLM
ANTHROPIC_API_KEY=...
LLM_PROVIDER=anthropic
INTENT_MODEL=claude-haiku
STRUCTURE_MODEL=claude-haiku
COMPARE_MODEL=claude-sonnet

# Embedding
EMBEDDING_MODEL=ko-sbert-multitask-klue-roberta-base
EMBEDDING_DIMENSION=768

# Service
NEXT_PUBLIC_APP_URL=http://localhost:3000
SEARCH_API_URL=http://localhost:8000

# Security
JWT_SECRET=...
RATE_LIMIT_ENABLED=true

# Cost control
MONTHLY_LLM_BUDGET_USD=200
```

---

## 9. 반드시 먼저 확정할 정책

개발 전에 아래 항목은 결정해야 한다. 이 부분이 흐리면 구현 중에 설계가 계속 흔들린다.

1. MVP 도메인: 임대차, 임금, 손해배상, 부당이득 중 어디까지 포함할지
2. 핵심 조문 목록: 도메인별 50~100개
3. 판례 원문 표시 범위: 원문 전체 표시 vs 공식 링크 우선
4. 법률 면책 고지 문구
5. 사용자 검색 로그 보존 기간
6. Free/Pro 기능 제한
7. 초기 임베딩 모델과 차원
8. LLM provider 장애 시 fallback
9. 관리자 검수 책임자와 검수 기준
10. 평가 데이터셋 라벨링 담당자

---

## 10. 검색 품질 기준

| 기능 | 지표 | MVP 목표 |
|------|------|----------|
| 조문 검색 | precision@10 | 0.80 이상 |
| 자연어 검색 | Top-5 관련 판례 수 | 평균 3건 이상 |
| 비교 후보 | Top-5 유효 비교 후보 수 | 평균 2건 이상 |
| 구조화 | facts/issue/outcome 정확도 | 0.75 이상 |
| 조문 추출 | hallucination 비율 | 3% 이하 |
| 검색 속도 | p95 latency | 2.5초 이하 |

품질 게이트는 CI에 넣되, 초기에는 경고만 표시하고 Phase 3부터 배포 차단 조건으로 사용한다.

---

## 11. LLM 사용 원칙

LLM은 법률 판단자가 아니라 구조화와 설명 보조 도구로만 사용한다.

허용:

- 자연어 intent 파싱
- 판례 원문 구조화
- 판례 카드 요약
- 비교 분기점 설명
- 검색 후보 재순위 보조

금지:

- 사용자 사건에 대한 법률 결론 단정
- 승소 가능성 수치화
- 원문 근거 없는 조문/판례 생성
- 공식 원문 확인 없이 단정적 해석 표시

검증:

- JSON Schema 검증
- 조문 실존 여부 검증
- `evidence_spans` 존재 여부 검증
- confidence 낮은 결과는 검수 큐 이동

---

## 12. UI 필수 화면

| 화면 | 설명 | MVP |
|------|------|-----|
| 검색 시작 화면 | 조문/자연어/사건번호 입력 | 예 |
| 검색 결과 화면 | 그룹별 판례 카드 | 예 |
| 기준 판례 선택 화면 | 비교 기준 선택 | 예 |
| 비교 후보 화면 | 유사/대비 판례 목록 | 예 |
| 판례 비교 화면 | 공통점, 차이점, 결과, 원문 근거 | 예 |
| 판례 상세 화면 | 구조화 정보와 공식 원문 링크 | 예 |
| 피드백 UI | 관련 있음/없음/요약 오류 | 예 |
| 관리자 검수 UI | 구조화 필드 수정, 재임베딩 | 이후 |

---

## 13. 로컬 개발 시작 순서

```bash
# 1. 레포 생성
mkdir caselens
cd caselens

# 2. 앱/패키지 디렉터리 생성
mkdir -p apps/web apps/search-api packages/prompts pipelines db/migrations docs infra scripts

# 3. Next.js 생성
cd apps
npx create-next-app@latest web --typescript

# 4. FastAPI 앱 생성
mkdir -p search-api/app
cd search-api
python -m venv .venv
pip install fastapi uvicorn pydantic sqlalchemy psycopg[binary] pgvector

# 5. DB 실행
docker compose up -d postgres

# 6. migration 실행
# scripts/migrate.sh 또는 alembic 사용
```

실제 명령은 운영체제/패키지 매니저에 맞게 조정한다.

---

## 14. 첫 번째 개발 마일스톤

첫 마일스톤은 “멋진 UI”가 아니라 검색 파이프라인이 끝까지 이어지는 것이다.

목표:

```text
사용자 조문 입력
→ 조문 정규화
→ DB에서 해당 조문 인용 판례 검색
→ 판례 카드 표시
→ 기준 판례 선택
→ 비교 후보 표시
→ 두 판례 비교 화면 표시
```

이 흐름이 샘플 데이터 100건으로 동작하면 MVP의 뼈대가 선다.

---

## 15. 아직 따로 작성해야 할 문서

이 착수 가이드는 새 프로젝트 시작용이다. 구현 전 아래 문서는 별도로 만들어야 한다.

| 문서 | 목적 |
|------|------|
| `DataCollectionPlan.md` | 수집 대상 조문, 키워드, 우선순위 |
| `EvaluationSet.md` | 검색/비교 품질 평가 세트 |
| `AdminReviewSpec.md` | 구조화 검수 UI와 운영 플로우 |
| `PromptRegistry.md` | 프롬프트 버전, 변경 이력, 평가 결과 |
| `LegalPolicy.md` | 저작권, 개인정보, 면책 고지 |
| `TestStrategy.md` | 테스트 계층과 CI 품질 게이트 |
| `DeploymentRunbook.md` | staging/production 배포 절차 |

---

## 16. 착수 전 최종 체크리스트

```text
[ ] MVP 도메인을 확정했다.
[ ] 초기 조문 목록을 확정했다.
[ ] 판례 원문 표시 정책을 정했다.
[ ] PostgreSQL + pgvector로 MVP를 시작하기로 확정했다.
[ ] Elasticsearch/Qdrant/Redis/Airflow는 MVP 이후로 미뤘다.
[ ] 초기 임베딩 모델과 차원을 고정했다.
[ ] LLM 사용 목적과 금지 범위를 정했다.
[ ] 검색 품질 평가 지표를 정했다.
[ ] 필수 면책 고지 문구를 정했다.
[ ] 첫 마일스톤의 end-to-end 흐름을 정했다.
```

