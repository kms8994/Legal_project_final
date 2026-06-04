# 평가와 QA 명세

## 1. 목표

CaseLens는 기능이 동작하는 것만으로 충분하지 않다. 검색 결과와 비교 후보의 품질을 측정해야 한다.

## 2. 평가 세트

MVP 초기:

| 세트 | 규모 | 목적 |
|------|------|------|
| 조문 검색 | 10개 조문 | 조문 매칭 정확도 |
| 자연어 검색 | 20개 질문 | intent/retrieval 품질 |
| 비교 후보 | 10개 기준 판례 | 사실관계 유사 후보 품질 |
| 구조화 검증 | 30건 | facts/material_facts/outcome 정확도 |

MVP 안정화 후:

| 세트 | 규모 |
|------|------|
| 조문 검색 | 30개 |
| 자연어 검색 | 50개 |
| 비교 후보 | 30쌍 |
| 구조화 검증 | 100건 |

## 3. 검색 평가 지표

### 조문 검색

- precision@10
- exact article match rate
- wrong statute rate

목표:

- precision@10 0.80 이상
- wrong statute rate 3% 이하

### 자연어 검색

- Top-5 관련 판례 수
- parsed intent accuracy
- validated article accuracy

목표:

- Top-5 관련 판례 평균 3건 이상

### 비교 후보

비교 후보는 다음을 따로 평가한다.

- fact similarity
- material fact match
- issue similarity
- outcome difference
- turning point clarity
- evidence coverage

목표:

- Top-5 중 사실관계 유사 후보 평균 3건 이상
- Top-5 중 결과 또는 판단 강도 차이 후보 평균 2건 이상
- Top-5 중 turning point 설명 가능 후보 평균 2건 이상

## 4. RAG/임베딩 검증

RAG와 임베딩 모델 검증은 코드 구현 이후 수행한다. 먼저 MVP 기본값으로 end-to-end 검색과 비교가 동작하게 만든 뒤, 같은 평가 세트에서 모델과 chunk 전략을 비교한다.

### 비교할 임베딩 후보

| 후보 | 검증 목적 |
|------|-----------|
| ko-sbert 계열 768차원 | MVP 기본값, 한국어 문장 유사도 기준선 |
| bge-m3 | 긴 문맥과 다국어 retrieval 품질 비교 |
| API embedding 모델 | 운영 편의성과 품질 기준선 비교 |

### 비교할 chunk 전략

| 전략 | 용도 |
|------|------|
| facts only | 사실관계 중심 검색 |
| facts + issue | 사실관계와 쟁점 결합 |
| material_facts only | 핵심 사실 중심 비교 |
| combined | facts, issue, material_facts, key_disputed_facts 결합 |
| paragraph-level | 생성용 evidence retrieval |

### 모델 비교 지표

- Recall@5
- MRR@10
- nDCG@10
- Top-5 fact similarity 평균
- Top-5 material fact match 평균
- Top-5 outcome difference 포함 수
- 검색 latency
- 임베딩 생성 비용

### 랭킹 가중치 실험

기본값은 균형형 Set B다.

```text
Set A: 벡터 중심
facts 0.50 / material 0.15 / event 0.10

Set B: 균형형
facts 0.35 / material 0.25 / event 0.15

Set C: material facts 중심
facts 0.25 / material 0.35 / event 0.20
```

material_facts 추출 품질이 낮으면 Set A를 우선하고, 추출 품질이 안정되면 Set C를 검토한다.

## 5. 구조화 평가

필드별로 평가한다.

- facts
- legal_issue
- material_facts
- key_disputed_facts
- outcome.direction
- outcome.key_factor
- evidence_spans

목표:

- 핵심 필드 정확도 0.75 이상
- evidence span 연결률 0.90 이상

## 6. 피드백 라벨

사용자 피드백 라벨:

- `relevant`
- `not_relevant`
- `facts_not_similar`
- `material_fact_missed`
- `wrong_statute`
- `outcome_not_different`
- `summary_error`
- `source_needed`

피드백은 검색 품질 개선과 재구조화 대상 선정에 사용한다.

## 7. 테스트 전략

### Backend unit test

- 조문 정규화
- 법령 alias resolve
- score 계산
- outcome difference 계산
- material fact match 계산
- LLM output validation

### Backend integration test

- 조문 검색 API
- 자연어 검색 API
- 비교 후보 API
- 비교 분석 API fallback
- 피드백 저장

### Pipeline test

- 중복 제거
- 문단 분리
- 조문 추출
- structure validation
- embedding content hash

### Frontend E2E

- 조문 검색 후 기준 판례 선택
- 자연어 검색 후 비교 후보 이동
- 비교 분석 화면 표시
- LLM timeout fallback 표시
- 피드백 제출

## 8. 품질 게이트

초기에는 경고만 표시한다. MVP 완성 단계부터 배포 차단 기준으로 쓴다.

차단 후보:

- 조문 검색 precision@10 0.70 미만
- 비교 후보 fact similarity 평균 목표 미달
- evidence span 연결률 0.80 미만
- LLM output invalid rate 10% 초과
- 검색 API p95 4초 초과

## 9. 완료 체크리스트

- [ ] 평가 세트가 파일 또는 DB로 관리된다.
- [ ] 평가 스크립트가 있다.
- [ ] 검색 품질 지표가 출력된다.
- [ ] 비교 후보 품질을 사람이 검토할 수 있다.
- [ ] RAG chunk 전략별 성능을 비교할 수 있다.
- [ ] 임베딩 모델 후보별 성능을 비교할 수 있다.
- [ ] 비교 랭킹 가중치 실험 결과가 기록된다.
- [ ] 피드백 라벨이 저장된다.
- [ ] QA 결과가 다음 개선 작업으로 연결된다.
