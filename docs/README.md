# CaseLens MVP 문서 인덱스

이 폴더는 CaseLens MVP를 실제로 구현할 때 계속 참조하기 위한 실행 문서 세트다. 기존 원본 문서인 `CaseLens_TechSpec_v03.md`, `caselens_new_project_start.md`의 내용을 통합하되, MVP 구현과 유지보수에 맞게 역할별 문서로 분리했다.

## 구현 기준

- MVP 도메인은 손해배상 중심으로 시작한다.
- 초기 데이터는 300~500건으로 시작하고, 파이프라인은 대량 적재를 전제로 재실행 가능하게 만든다.
- 검색/비교는 RAG 구조를 사용한다.
- 판례 비교 추천은 결과 차이보다 사실관계와 material facts 유사도를 최우선으로 둔다.
- 결과가 다르다는 점은 비교 후보 필터와 사용자 표시 조건으로 사용하되, 추천 점수의 중심이 되어서는 안 된다.
- MVP 인프라는 Next.js, FastAPI, PostgreSQL 16, pgvector, Python CLI 파이프라인으로 고정한다.
- Elasticsearch, Qdrant, Redis, Airflow, 결제, 대규모 관리자 시스템은 MVP 이후 단계로 둔다.

## 문서 목록

| 문서 | 목적 |
|------|------|
| `PRD.md` | 제품 목표, 사용자, MVP 범위, 성공 기준 |
| `DevelopmentPlan.md` | 처음부터 MVP 완성까지의 구현 순서 |
| `Architecture.md` | 전체 시스템 구조와 서비스 간 책임 |
| `BackendSpec.md` | FastAPI Search API와 Next.js BFF 구현 기준 |
| `FrontendSpec.md` | Next.js 화면, 상태, API 연동 기준 |
| `DatabaseSpec.md` | PostgreSQL/pgvector 스키마, 인덱스, 마이그레이션 기준 |
| `DataPipelineSpec.md` | 수집, 정규화, 구조화, 임베딩, 적재 파이프라인 |
| `RAGAndRankingSpec.md` | RAG 로직, retrieval, 유사도 가중치, 비교 후보 랭킹 |
| `UIUXSpec.md` | 화면별 UX, 비교 UI, 예외 UX, 접근성 기준 |
| `EvaluationAndQA.md` | 평가 데이터셋, 품질 지표, 테스트 전략 |
| `OperationsMaintenance.md` | 유지보수, 재수집, 재임베딩, 장애 대응 |
| `StatuteScope.md` | MVP 조문 목록과 데이터 수집 우선순위 |
| `MaterialFactsTemplates.md` | 손해배상 세부 유형별 material facts 템플릿 |
| `PromptRegistry.md` | MVP LLM 프롬프트와 출력 스키마 |
| `EvaluationSet.md` | 초기 평가 세트 초안과 라벨링 기준 |
| `LegalPolicy.md` | 원문 표시, 개인정보, 면책 고지 정책 |
| `SelfReview.md` | 현재 문서 세트의 부족한 부분과 보완 과제 |

## 추천 읽는 순서

1. `PRD.md`
2. `DevelopmentPlan.md`
3. `Architecture.md`
4. `DatabaseSpec.md`
5. `DataPipelineSpec.md`
6. `RAGAndRankingSpec.md`
7. `BackendSpec.md`
8. `FrontendSpec.md`
9. `UIUXSpec.md`
10. `EvaluationAndQA.md`
11. `OperationsMaintenance.md`
12. `StatuteScope.md`
13. `MaterialFactsTemplates.md`
14. `PromptRegistry.md`
15. `EvaluationSet.md`
16. `LegalPolicy.md`
17. `SelfReview.md`
