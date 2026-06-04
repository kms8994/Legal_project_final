# Backend 구현 명세

## 1. 백엔드 구성

백엔드는 두 계층으로 나눈다.

```text
Next.js API Routes / BFF
FastAPI Search API
```

BFF는 프론트 친화적인 입출력, rate limit, 인증을 담당한다. FastAPI는 검색, RAG, 비교, 데이터 접근을 담당한다.

## 2. FastAPI 모듈 구조

```text
apps/search-api/app/
  api/
    health.py
    search.py
    cases.py
    compare.py
    feedback.py
    pipeline.py
  core/
    config.py
    errors.py
    logging.py
    security.py
  schemas/
    search.py
    case.py
    compare.py
    feedback.py
  services/
    article_normalizer.py
    intent_parser.py
    retrieval.py
    ranking.py
    evidence.py
    rag_generation.py
    comparison.py
    llm.py
    embeddings.py
  db/
    session.py
    repositories/
```

## 3. API 목록

### Health

```http
GET /health
```

응답:

```json
{
  "status": "ok",
  "db": "ok",
  "version": "mvp"
}
```

### 조문 검색

```http
POST /api/v1/search/statute
```

요청:

```json
{
  "query": "민법 제750조",
  "page": 1,
  "size": 20,
  "sort": "relevance"
}
```

응답:

```json
{
  "query": {
    "raw": "민법 제750조",
    "normalized_ref": "민법_제750조",
    "article_validated": true
  },
  "results": [
    {
      "case_id": "uuid",
      "case_no": "2021다12345",
      "court_name": "대법원",
      "decision_date": "2022-03-15",
      "case_name": "손해배상",
      "summary_card": "근거 기반 요약",
      "outcome": {
        "disposition": "일부 인용",
        "direction": "원고 일부 유리",
        "key_factor": "피해자 과실"
      },
      "cited_articles": ["민법_제750조"],
      "score": 0.91,
      "evidence_ids": ["p12", "p18"]
    }
  ]
}
```

### 자연어 검색

```http
POST /api/v1/search/natural
```

요청:

```json
{
  "query": "교통사고 피해자인데 무단횡단이 일부 문제된 손해배상 판례",
  "page": 1,
  "size": 20
}
```

응답:

```json
{
  "parsed_intent": {
    "case_type": "민사",
    "legal_domain": "손해배상",
    "keywords": ["교통사고", "과실상계", "손해배상"],
    "legal_issue": "피해자 과실이 손해배상 범위에 미치는 영향",
    "inferred_articles": ["민법_제750조", "민법_제396조"],
    "inferred_articles_validated": true,
    "facts_summary": "교통사고 피해자의 무단횡단 여부가 과실상계에서 문제된 사안",
    "confidence": 0.82
  },
  "search_method": "hybrid_rag",
  "results": []
}
```

### 판례 상세

```http
GET /api/v1/cases/{case_id}
```

응답에는 metadata, structured fields, material_facts, outcome, facets, paragraphs, source_url, review status를 포함한다.

### 비교 후보

```http
GET /api/v1/cases/{case_id}/compare-candidates
```

쿼리:

```text
limit=5
require_outcome_difference=true
```

응답:

```json
{
  "base_case": {
    "case_id": "uuid",
    "summary_card": "기준 판례 요약",
    "material_facts": {}
  },
  "candidates": [
    {
      "case_id": "uuid",
      "summary_card": "비교 후보 요약",
      "scores": {
        "facts_vector_similarity": 0.87,
        "material_fact_match": 0.82,
        "issue_similarity": 0.79,
        "outcome_difference": 1.0,
        "final_score": 0.84
      },
      "common_facts": ["차량 대 보행자 사고", "피해자 과실 여부 다툼"],
      "possible_turning_points": ["무단횡단 인정 여부"],
      "outcome_difference_summary": "기준 판례는 과실을 낮게 보았고, 후보 판례는 피해자 과실을 높게 보았습니다."
    }
  ]
}
```

### 판례 비교

```http
POST /api/v1/compare
```

요청:

```json
{
  "base_case_id": "uuid",
  "compare_case_id": "uuid"
}
```

응답:

```json
{
  "base": {},
  "compare": {},
  "analysis": {
    "common_points": [],
    "material_differences": [],
    "turning_points": [],
    "result_difference": "결과 차이 설명",
    "generated_by": "llm",
    "fallback_used": false
  },
  "evidence_links": {},
  "disclaimer": "참고용 정보입니다."
}
```

### 피드백

```http
POST /api/v1/feedback
```

라벨:

- `relevant`
- `not_relevant`
- `facts_not_similar`
- `material_fact_missed`
- `wrong_statute`
- `outcome_not_different`
- `summary_error`
- `source_needed`

## 4. 백엔드 서비스 로직

### 조문 검색

1. 입력 문자열 정리
2. 법령명/조문 번호 파싱
3. law_aliases에서 법령 resolve
4. articles에서 존재 여부 검증
5. cited_articles GIN 검색
6. issue/facts 보조 점수 계산
7. evidence 문단 선택
8. 요약 캐시 확인
9. LLM 요약 또는 fallback 요약 반환

주의:

- 조문 검증은 내부 DB의 `laws`, `law_aliases`, `articles`만 사용한다.
- FastAPI 런타임에서는 법령정보센터 API를 직접 호출하지 않는다.
- 법령정보센터 API는 로컬/배치 수집 파이프라인에서만 사용한다.

### 자연어 검색

1. 사용자 입력 길이 제한
2. intent parser 호출
3. inferred_articles 검증
4. BM25 또는 full-text 검색
5. facts vector 검색
6. issue vector 검색
7. facet filter
8. RRF 또는 weighted score
9. evidence retrieval
10. 결과 카드 생성

### 비교 후보 추천

1. 기준 판례 구조화 결과 로드
2. 같은 legal_domain, case_type 후보 필터
3. facts vector 상위 100개 검색
4. material_facts match 계산
5. event_structure match 계산
6. issue/statute/facet 보조 점수 계산
7. outcome difference flag 계산
8. final score 정렬
9. 결과 다른 후보 우선 표시
10. 부족하면 완화 정책 적용

### 비교 분석 생성

1. 두 판례의 facts, issue, reasoning, outcome 문단 retrieval
2. material_facts와 key_disputed_facts 로드
3. LLM 비교 프롬프트 구성
4. JSON Schema 검증
5. evidence id 검증
6. 실패 시 fallback 표 생성

## 5. 오류 처리

| 코드 | HTTP | 처리 |
|------|------|------|
| `PARSE_FAILED` | 400 | 조문 형식 안내 |
| `ARTICLE_NOT_FOUND` | 404 | 공식 법령 검색 링크 제공 |
| `CASE_NOT_FOUND` | 404 | 판례 없음 |
| `LOW_CONFIDENCE_INTENT` | 200 | 추가 설명 요청 문구 포함 |
| `NO_RESULTS` | 200 | 조건 완화 제안 |
| `LLM_TIMEOUT` | 200 | fallback_used true |
| `SEARCH_UNAVAILABLE` | 503 | 재시도 가능 |
| `RATE_LIMITED` | 429 | 남은 시간 표시 |

## 6. 구현 완료 체크리스트

- [ ] API schema가 문서와 일치한다.
- [ ] 모든 LLM 출력은 검증된다.
- [ ] LLM 실패 시 fallback이 있다.
- [ ] 비교 후보 점수에서 outcome difference 비중이 낮다.
- [ ] material fact 누락 피드백을 저장한다.
- [ ] 검색 로그에 query, latency, result_count가 저장된다.
- [ ] 비용 추적을 위해 llm_runs가 저장된다.
