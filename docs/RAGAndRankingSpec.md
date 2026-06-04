# RAG와 유사도 랭킹 명세

## 1. 핵심 원칙

CaseLens의 RAG는 일반 챗봇이 아니다. 판례 검색과 비교를 근거 기반으로 수행하기 위한 구조다.

```text
사용자 입력
→ query understanding
→ retrieval
→ ranking
→ evidence selection
→ generation
→ validation
→ UI 표시
```

LLM은 검색된 근거 밖의 내용을 말하면 안 된다.

## 2. RAG 저장 단위

### case-level

- 판례 메타데이터
- 사건 유형
- 법률 도메인
- outcome
- facets
- 구조화 요약

### paragraph-level

- 원문 문단
- section_type
- char offset
- evidence id

### structure-level

- facts
- facts_timeline
- actors
- actions
- harm
- causation
- legal_issue
- court_reasoning
- conclusion
- material_facts
- key_disputed_facts
- aggravating_factors
- mitigating_factors

### embedding-level

- facts_vector
- issue_vector
- reasoning_vector
- material_facts_vector
- combined_vector
- paragraph_vector

## 3. 검색용 RAG 로직

```text
사용자 입력
→ 조문/자연어/사건번호 판별
→ 조문 정규화 또는 intent parsing
→ 후보 retrieval
→ 유사도/메타 점수 계산
→ evidence 문단 선택
→ 판례 카드 요약 생성
```

## 4. 비교용 RAG 로직

```text
기준 판례 선택
→ 같은 legal_domain/case_type 후보 필터
→ facts vector 상위 후보 검색
→ material facts 정밀 매칭
→ issue/statute/facet 보조 점수
→ outcome difference flag 적용
→ 후보 Top 5
→ 두 판례 evidence retrieval
→ 비교 분석 생성
```

## 5. 생성용 RAG 컨텍스트

LLM에는 전체 판례 원문을 넣지 않는다. 다음 근거만 넣는다.

기준 판례:

- facts 문단 2~3개
- issue 문단 1개
- reasoning 문단 2~3개
- order/outcome 문단 1개
- material_facts
- key_disputed_facts

비교 판례:

- 동일 구조

추가 메타:

- cited_articles
- outcome.direction
- outcome.key_factor
- facets
- confidence_score

## 6. 조문 검색 가중치

조문 검색은 정확한 조문 매칭이 최우선이다.

```text
exact_article_match       0.45
same_law_near_article     0.10
bm25_keyword_score        0.15
issue_vector_score        0.10
facts_vector_score        0.10
court_recency_weight      0.05
court_level_weight        0.05
```

규칙:

- exact_article_match가 없는 판례는 상위 노출을 제한한다.
- inferred article은 자연어 검색에서만 보조 신호로 사용한다.

## 7. 자연어 검색 가중치

자연어 검색은 사실관계와 법적 쟁점을 같이 본다.

```text
facts_vector_score        0.35
bm25_keyword_score        0.25
issue_vector_score        0.15
validated_article_match   0.10
facet_match_score         0.10
case_type_match_score     0.05
```

주의:

- LLM이 추정한 조문은 법령 DB에서 검증된 경우만 반영한다.
- confidence가 낮은 intent는 조문/유형 점수를 낮춘다.

## 8. 비교 후보 가중치

비교 후보 추천은 사실관계 유사도가 중심이다. 결과 차이는 필터와 표시 조건에 가깝다.

```text
facts_vector_similarity       0.35
material_fact_match_score     0.25
event_structure_match_score   0.15
issue_similarity              0.10
statute_overlap               0.07
facet_match_score             0.05
outcome_difference_flag       0.03
```

이 가중치는 의도적으로 outcome 비중을 낮게 둔다. 결과가 다른 판례라도 사실관계가 덜 유사하면 좋은 비교 후보가 아니다.

## 9. material fact match

material fact는 법률 판단에 영향을 주는 중요한 사실이다.

손해배상 예시:

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

형사 확장 시 예시:

```json
{
  "crime_type": "상해",
  "intent_level": "미필적 고의",
  "weapon_used": true,
  "injury_severity": "전치 4주",
  "victim_vulnerability": false,
  "prior_record": true,
  "provocation": true,
  "settlement": false,
  "confession": true,
  "recidivism_period": true
}
```

## 10. event structure match

event structure는 사건의 논리 구조다.

```text
누가
누구에게
어떤 행위를 했고
어떤 피해가 발생했으며
그 행위와 피해 사이 인과관계가 어떻게 다투어졌는가
```

두 판례의 사건 구조가 같아야 진짜 비교 가치가 있다.

## 11. outcome difference

결과 차이는 다음처럼 계산한다.

```text
direction 다름            +0.45
claim_result 다름         +0.25
key_factor 다름           +0.20
amount/ratio 차이 있음    +0.10
```

하지만 최종 비교 후보 점수에서는 0.03만 반영한다. 결과 차이는 후보를 설명하고 필터링하는 조건이지, 사실관계 유사성을 이기면 안 된다.

## 12. 후보 완화 정책

비교 후보가 부족할 때 순서대로 완화한다.

```text
1. 같은 legal_domain + 같은 주요 조문 + 높은 material_fact_match + outcome difference
2. 같은 legal_domain + 높은 facts_vector_similarity + outcome difference
3. 같은 legal_domain + 높은 issue_similarity
4. 같은 키워드 cluster 내 대표 비교 후보
```

완화 단계는 UI에 반드시 표시한다.

## 13. LLM 비교 프롬프트 규칙

LLM 지시:

```text
1. 제공된 evidence 안의 내용만 사용한다.
2. 근거가 없는 내용은 "원문 근거 부족"으로 표시한다.
3. 공통 사실관계와 차이점을 구분한다.
4. 결과가 달라진 미세 차이를 최대 3개 추출한다.
5. 각 주장에 evidence id를 붙인다.
6. 법률 조언이나 승소 가능성 예측을 하지 않는다.
7. 결과 차이는 판례 간 비교로만 설명한다.
```

## 14. 평가 기준

비교 후보 평가 시 다음을 따로 본다.

- fact similarity
- material fact match
- issue similarity
- outcome difference
- turning point quality
- evidence coverage

Top-5에 결과가 다른 판례가 있어도 사실관계가 부정확하면 실패로 본다.

