# Database 구현 명세

## 1. DB 목표

PostgreSQL 16 + pgvector로 MVP의 메타데이터, 원문, 문단, 구조화 결과, 임베딩, 로그를 모두 저장한다. 나중에 데이터가 많아져도 재수집, 재구조화, 재임베딩이 가능해야 한다.

## 2. 핵심 원칙

- 원문은 항상 저장한다.
- 파생 결과는 버전과 hash를 남긴다.
- 임베딩 모델과 차원은 반드시 저장한다.
- LLM 결과는 prompt_version, model_name, confidence를 저장한다.
- 삭제보다 soft delete와 재처리를 우선한다.
- 사용자 노출 AI 텍스트는 evidence span과 연결한다.

## 3. 핵심 테이블

### cases

판례 원문과 기본 메타데이터.

필드:

- `id`
- `external_id`
- `case_no`
- `court_name`
- `court_level`
- `decision_date`
- `case_name`
- `case_type`
- `legal_domain`
- `source`
- `source_url`
- `raw_text`
- `raw_html`
- `source_hash`
- `pipeline_run_id`
- `is_deleted`
- `collected_at`
- `created_at`
- `updated_at`

unique:

- `case_no`, `decision_date`, `court_name`
- `source_hash`

### case_paragraphs

RAG retrieval의 최소 원문 근거 단위.

필드:

- `id`
- `case_id`
- `paragraph_id`
- `section_type`
- `paragraph_order`
- `text`
- `char_start`
- `char_end`
- `content_hash`

section_type 후보:

- `facts`
- `issue`
- `reasoning`
- `order`
- `claim`
- `unknown`

### case_structures

구조화 결과.

필드:

- `id`
- `case_id`
- `cited_articles`
- `referenced_cases`
- `facts`
- `facts_timeline`
- `actors`
- `actions`
- `harm`
- `causation`
- `legal_issue`
- `court_reasoning`
- `conclusion`
- `material_facts`
- `aggravating_factors`
- `mitigating_factors`
- `key_disputed_facts`
- `outcome`
- `facets`
- `evidence_spans`
- `confidence_score`
- `review_status`
- `is_reviewed`
- `prompt_version`
- `model_name`
- `structure_hash`
- `processed_at`

### case_embeddings

검색용 임베딩.

필드:

- `id`
- `case_id`
- `paragraph_id`
- `embedding_type`
- `embedding_model`
- `embedding_dimension`
- `content_text`
- `content_hash`
- `embedding vector(768)`
- `needs_regeneration`
- `created_at`

embedding_type:

- `facts`
- `issue`
- `reasoning`
- `material_facts`
- `combined`
- `paragraph`

### laws

법령 정보.

필드:

- `id`
- `law_code`
- `official_name`
- `short_name`
- `effective_date`
- `source_url`

### law_aliases

법령 약칭.

필드:

- `id`
- `law_id`
- `alias`

### articles

조문 정보.

필드:

- `id`
- `law_id`
- `article_code`
- `article_no`
- `article_branch_no`
- `paragraph_no`
- `subparagraph_no`
- `title`
- `body`
- `normalized_ref`
- `effective_date`

법령과 조문 데이터는 법령정보센터 API를 로컬/배치 파이프라인에서 호출해 채운다. 런타임 백엔드는 외부 API를 호출하지 않고 이 테이블만 조회한다.

### search_queries

검색 로그.

필드:

- `id`
- `user_id`
- `query_text`
- `query_type`
- `parsed_query`
- `result_count`
- `latency_ms`
- `created_at`

### comparison_feedbacks

비교/검색 피드백.

필드:

- `id`
- `user_id`
- `query_id`
- `base_case_id`
- `compare_case_id`
- `label`
- `reason`
- `comment`
- `created_at`

### llm_runs

LLM 호출 기록.

필드:

- `id`
- `purpose`
- `model_name`
- `prompt_version`
- `input_hash`
- `output`
- `latency_ms`
- `token_input`
- `token_output`
- `cost_usd`
- `status`
- `error_message`
- `created_at`

### pipeline_runs

파이프라인 실행 기록.

필드:

- `id`
- `stage`
- `status`
- `source`
- `params`
- `started_at`
- `finished_at`
- `input_count`
- `success_count`
- `failed_count`
- `error_summary`

### prompt_versions

프롬프트 버전 관리.

필드:

- `id`
- `name`
- `version`
- `purpose`
- `content_hash`
- `created_at`
- `notes`

## 4. JSONB 구조

### material_facts 예시

```json
{
  "accident_type": "차량 대 보행자",
  "victim_status": "보행자",
  "defendant_conduct": "전방주시 태만",
  "victim_conduct": "무단횡단",
  "injury_type": "신체 상해",
  "causation_dispute": true,
  "negligence_offset_issue": true,
  "insurance_status": "불명",
  "damage_scope_issue": "치료비 및 위자료"
}
```

### outcome 예시

```json
{
  "disposition": "일부 인용",
  "direction": "원고 일부 유리",
  "claim_result": "일부 인용",
  "relief_type": "손해배상",
  "amount_claimed": null,
  "amount_awarded": null,
  "ratio_or_percentage": "피해자 과실 30%",
  "key_factor": "피해자 과실",
  "confidence": 0.82
}
```

### facets 예시

```json
{
  "legal_domain": "손해배상",
  "case_type": "민사",
  "key_parties": ["개인", "개인"],
  "harm_type": "신체",
  "causal_relation": "직접",
  "contract_relation": false,
  "court_level": "대법원"
}
```

## 5. 주요 인덱스

- `cases(case_no)`
- `cases(decision_date desc)`
- `cases(court_level)`
- `cases(legal_domain)`
- `case_structures using gin(cited_articles)`
- `case_structures using gin(outcome)`
- `case_structures using gin(facets)`
- `case_structures using gin(material_facts)`
- `case_paragraphs(case_id, paragraph_order)`
- `articles(normalized_ref)`
- `case_embeddings using ivfflat (embedding vector_cosine_ops)`

## 6. 마이그레이션 순서

1. extension 활성화: `pgcrypto`, `vector`
2. 법령 테이블 생성
3. 판례 원문 테이블 생성
4. 문단 테이블 생성
5. 구조화 테이블 생성
6. 임베딩 테이블 생성
7. 로그/피드백/LLM/pipeline 테이블 생성
8. 인덱스 생성
9. seed 데이터 삽입

## 7. 완료 체크리스트

- [ ] pgvector가 활성화되어 있다.
- [ ] 원문과 문단이 cascade로 연결된다.
- [ ] `material_facts`, `outcome`, `facets`가 JSONB로 저장된다.
- [ ] 임베딩 모델과 차원이 저장된다.
- [ ] source_hash로 중복을 막는다.
- [ ] pipeline_runs로 재처리 이력을 추적한다.
