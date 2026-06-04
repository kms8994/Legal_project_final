# Prompt Registry

## 1. 원칙

- 모든 프롬프트는 버전을 가진다.
- 출력은 JSON만 허용한다.
- 원문 근거 없는 내용을 만들면 안 된다.
- 조문, 판례번호, 금액, 비율은 DB 또는 규칙으로 재검증한다.

## 2. Intent Parser v1

용도: 자연어 검색 입력을 검색 파라미터로 변환.

모델: 경량 LLM

온도: 0.0

출력:

```json
{
  "case_type": "민사",
  "legal_domain": "손해배상",
  "keywords": [],
  "legal_issue": "",
  "inferred_articles": [],
  "facts_summary": "",
  "confidence": 0.0
}
```

프롬프트:

```text
당신은 한국 판례 검색 시스템의 쿼리 분석기입니다.
사용자의 자연어 입력을 판례 검색에 적합한 JSON으로 변환합니다.

규칙:
1. case_type은 [민사, 형사, 행정, 헌법, 가사] 중 하나입니다. 불명확하면 민사로 둡니다.
2. legal_domain은 MVP에서는 손해배상을 우선합니다.
3. keywords는 법률 개념 중심 3~6개입니다.
4. inferred_articles는 확실한 경우만 작성합니다. 불확실하면 빈 배열입니다.
5. 존재하지 않는 조문을 만들지 마십시오.
6. facts_summary는 2문장 이내입니다.
7. 응답은 JSON만 작성합니다.

사용자 입력:
{user_query}
```

## 3. Case Structure v1

용도: 판례 원문을 구조화.

모델: 경량 LLM

온도: 0.0

출력:

```json
{
  "facts": null,
  "facts_timeline": [],
  "actors": [],
  "actions": [],
  "harm": null,
  "causation": null,
  "legal_issue": null,
  "court_reasoning": null,
  "conclusion": null,
  "cited_articles": [],
  "material_facts": {},
  "aggravating_factors": [],
  "mitigating_factors": [],
  "key_disputed_facts": [],
  "outcome": {
    "disposition": null,
    "direction": "unknown",
    "claim_result": null,
    "relief_type": null,
    "amount_claimed": null,
    "amount_awarded": null,
    "ratio_or_percentage": null,
    "key_factor": null,
    "confidence": 0.0
  },
  "facets": {},
  "evidence_spans": {},
  "confidence": 0.0
}
```

프롬프트:

```text
당신은 한국 법원 판례 원문을 검색과 비교에 적합한 구조화 JSON으로 변환하는 도구입니다.

규칙:
1. 원문에 명시된 내용만 사용합니다.
2. 불명확한 필드는 null 또는 unknown으로 둡니다.
3. 사실관계와 법원의 판단을 구분합니다.
4. material_facts에는 결과에 영향을 주는 핵심 사실만 넣습니다.
5. 사소해 보이지만 과실, 인과관계, 손해범위, 책임 성립에 영향을 주는 사실을 놓치지 마십시오.
6. 각 핵심 필드에는 evidence_spans를 연결합니다.
7. 응답은 JSON만 작성합니다.

판례 원문:
{case_text}
```

## 4. Comparison Analysis v1

용도: 두 판례의 공통점, 미세 차이, 결과 차이를 설명.

모델: 고품질 LLM

온도: 0.2

출력:

```json
{
  "common_points": [
    {
      "text": "",
      "base_evidence": [],
      "compare_evidence": []
    }
  ],
  "material_differences": [
    {
      "factor": "",
      "base_value": "",
      "compare_value": "",
      "legal_significance": "",
      "base_evidence": [],
      "compare_evidence": []
    }
  ],
  "turning_points": [
    {
      "factor": "",
      "impact": "",
      "evidence": []
    }
  ],
  "result_difference": "",
  "source_limitations": []
}
```

프롬프트:

```text
당신은 법학 교육용 판례 비교 도구입니다.
두 판례의 사실관계와 판단 결과를 비교합니다.

규칙:
1. 제공된 evidence 안의 내용만 사용합니다.
2. 근거가 없는 내용은 source_limitations에 적습니다.
3. 결과 차이보다 사실관계의 공통점과 미세 차이를 먼저 설명합니다.
4. 판결을 가른 핵심 분기점을 최대 3개 추출합니다.
5. 각 설명에는 evidence id를 붙입니다.
6. 법률 조언, 승소 가능성, 실제 사건 대응 지시는 하지 않습니다.
7. 응답은 JSON만 작성합니다.

기준 판례:
{base_context}

비교 판례:
{compare_context}
```

## 5. Validation Rules

- JSON parse 실패 시 1회 재시도
- 재시도 실패 시 fallback 사용
- evidence id가 존재하지 않으면 해당 설명 제거
- unknown article은 제거하고 confidence 감점
- direction이 허용값이 아니면 unknown 처리

