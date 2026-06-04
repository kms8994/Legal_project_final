# CaseLens 아키텍처 명세

## 1. 전체 구조

```text
사용자
→ Next.js Web
→ Next.js API Routes / BFF
→ FastAPI Search API
→ PostgreSQL 16 + pgvector
→ Python Data Pipeline
→ LLM / Embedding Model
```

MVP에서는 서비스를 과하게 분리하지 않는다. Next.js는 사용자 경험과 BFF, FastAPI는 검색, 비교, RAG, 파이프라인 연동을 담당한다.

## 2. 컴포넌트 책임

### Next.js Web

- 검색 시작 화면
- 검색 결과 화면
- 기준 판례 선택
- 비교 후보 화면
- 비교 분석 화면
- 판례 상세 화면
- 피드백 UI
- 면책 고지 표시

### Next.js BFF

- 클라이언트 요청 검증
- 사용자 세션 또는 익명 사용자 식별
- rate limit
- FastAPI 프록시
- 프론트에 맞는 응답 shape 조정

### FastAPI Search API

- 조문 정규화
- 자연어 intent parsing
- hybrid retrieval
- RAG evidence retrieval
- 판례 카드 요약
- 비교 후보 추천
- 비교 분석 생성
- 피드백 저장
- pipeline 상태 조회

FastAPI Search API는 MVP 런타임에서 법령정보센터 API를 직접 호출하지 않는다. 법령과 판례 데이터는 로컬/배치 파이프라인으로 미리 수집해 DB에 저장하고, 런타임 API는 내부 DB만 조회한다.

### PostgreSQL + pgvector

- 판례 원문 저장
- 문단 저장
- 구조화 JSON 저장
- 조문/법령 저장
- 임베딩 저장
- 검색 로그 저장
- 피드백 저장
- 파이프라인 실행 이력 저장

### Python Pipeline

- 수집
- 정규화
- 문단 분리
- 규칙 기반 추출
- LLM 구조화
- 검증
- 임베딩 생성
- 적재
- 재처리

법령정보센터 API 호출은 이 계층에서만 수행한다. 수집 스크립트를 로컬 또는 배치 작업으로 실행해 `laws`, `articles`, `cases`, `case_paragraphs`를 채운다.

## 3. MVP 기술 결정

| 영역 | 결정 |
|------|------|
| Frontend | Next.js + TypeScript |
| BFF | Next.js API Routes |
| Search API | FastAPI |
| DB | PostgreSQL 16 |
| Vector | pgvector |
| Pipeline | Python CLI |
| Scheduler | 수동 실행 또는 cron |
| LLM | Provider adapter 구조 |
| Embedding | 768차원 단일 모델 |
| Cache | MVP에서는 DB/메모리 캐시 최소 사용 |
| 전문 검색 | PostgreSQL full-text 또는 단순 키워드 검색 |

## 4. 데이터 흐름

### 검색 데이터 흐름

```text
사용자 입력
→ BFF request validation
→ FastAPI query understanding
→ internal DB retrieval
→ ranking
→ evidence selection
→ optional LLM summary
→ response
→ UI render
```

런타임 검색 중 외부 법령 API 호출은 하지 않는다.

### 비교 데이터 흐름

```text
기준 판례
→ 후보 retrieval
→ fact/material fact reranking
→ outcome difference filtering
→ 후보 Top 5
→ 사용자 비교 대상 선택
→ evidence retrieval
→ LLM comparison generation
→ validation
→ UI render
```

### 파이프라인 데이터 흐름

```text
source API
→ raw case
→ normalized text
→ paragraphs
→ extracted articles
→ structured fields
→ material facts
→ validation
→ embeddings
→ indexes
```

## 5. 확장 전략

MVP 구조를 유지하면서 다음처럼 확장한다.

| 필요 | 확장 |
|------|------|
| 검색량 증가 | Redis cache |
| 전문 검색 품질 필요 | Elasticsearch |
| 벡터 검색 대규모화 | Qdrant |
| 파이프라인 복잡도 증가 | Airflow, Prefect, Dagster |
| 검수 업무 증가 | Admin Review UI |
| 다중 모델 실험 | prompt/model registry 고도화 |

## 6. 주요 비기능 요구사항

- 검색 p95 2.5초 이하
- 비교 분석 LLM 성공 시 10초 이내
- LLM 실패 시 fallback 응답
- 모든 사용자 노출 AI 텍스트는 evidence 기반
- 파이프라인 단계별 재실행 가능
- 모델/프롬프트/임베딩 버전 추적 가능
- 대량 데이터 적재 시 기존 데이터 중복 방지
