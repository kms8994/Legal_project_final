# CaseLens API 계약과 Fixture

## 1. 목적

이 문서는 MVP 프론트엔드와 FastAPI Search API 사이의 입출력 계약을 고정한다. 법령정보센터 API 응답은 수집 파이프라인에서만 사용하고, 런타임 검색 API는 내부 PostgreSQL DB만 조회한다.

## 2. 공통 규칙

- Base path: `/api/v1`
- Content-Type: `application/json; charset=utf-8`
- 날짜 형식: `YYYY-MM-DD`
- ID 형식: 내부 DB `uuid`
- 페이지는 1부터 시작한다.
- `score`는 API 응답에 포함할 수 있으나 MVP UI에서는 기본 노출하지 않는다.
- 모든 사용자 노출 AI 텍스트는 가능한 경우 `evidence_ids`를 포함한다.

## 3. 공통 타입

### CaseCard

```json
{
  "case_id": "11111111-1111-1111-1111-111111111111",
  "case_no": "2021다12345",
  "court_name": "대법원",
  "court_level": "supreme",
  "decision_date": "2022-03-15",
  "case_name": "손해배상",
  "case_type": "민사",
  "legal_domain": "손해배상",
  "summary_card": "교통사고 피해자의 과실상계가 손해배상 범위에서 문제된 사안입니다.",
  "outcome": {
    "disposition": "일부 인용",
    "direction": "원고 일부 유리",
    "claim_result": "일부 인용",
    "key_factor": "피해자 과실"
  },
  "cited_articles": ["민법_제750조", "민법_제396조"],
  "evidence_ids": ["p12", "p18"],
  "source_url": "https://www.law.go.kr/precInfoP.do?precSeq=000000",
  "review_status": "pending",
  "confidence_score": 0.82
}
```

### EvidenceParagraph

```json
{
  "evidence_id": "p12",
  "paragraph_id": "22222222-2222-2222-2222-222222222222",
  "section_type": "reasoning",
  "paragraph_order": 12,
  "text": "원문 근거 문단 일부입니다.",
  "char_start": 1200,
  "char_end": 1450
}
```

### ErrorResponse

```json
{
  "error": {
    "code": "ARTICLE_NOT_FOUND",
    "message": "내부 법령 DB에서 해당 조문을 찾을 수 없습니다.",
    "details": {
      "query": "민법 제9999조"
    }
  }
}
```

## 4. Health

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

## 5. 조문 검색

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

응답 fixture:

```json
{
  "query": {
    "raw": "민법 제750조",
    "mode": "statute",
    "normalized_ref": "민법_제750조",
    "law_name": "민법",
    "article_no": "750",
    "article_validated": true
  },
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 128,
    "has_next": true
  },
  "results": [
    {
      "case_id": "11111111-1111-1111-1111-111111111111",
      "case_no": "2021다12345",
      "court_name": "대법원",
      "court_level": "supreme",
      "decision_date": "2022-03-15",
      "case_name": "손해배상",
      "case_type": "민사",
      "legal_domain": "손해배상",
      "summary_card": "전방주시 의무 위반과 피해자 과실이 함께 문제된 손해배상 사안입니다.",
      "outcome": {
        "disposition": "일부 인용",
        "direction": "원고 일부 유리",
        "claim_result": "일부 인용",
        "key_factor": "피해자 과실"
      },
      "cited_articles": ["민법_제750조", "민법_제396조"],
      "score": 0.91,
      "evidence_ids": ["p12", "p18"],
      "source_url": "https://www.law.go.kr/precInfoP.do?precSeq=000000",
      "review_status": "pending",
      "confidence_score": 0.82
    }
  ]
}
```

오류:

- `PARSE_FAILED` 400
- `ARTICLE_NOT_FOUND` 404
- `SEARCH_UNAVAILABLE` 503

## 6. 자연어 검색

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

응답 fixture:

```json
{
  "parsed_intent": {
    "case_type": "민사",
    "legal_domain": "손해배상",
    "keywords": ["교통사고", "무단횡단", "과실상계", "손해배상"],
    "legal_issue": "피해자 과실이 손해배상 범위에 미치는 영향",
    "inferred_articles": ["민법_제750조", "민법_제396조"],
    "inferred_articles_validated": true,
    "facts_summary": "교통사고 피해자의 무단횡단 여부가 과실상계에서 문제된 사안",
    "confidence": 0.82
  },
  "search_method": "hybrid_rag",
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 42,
    "has_next": true
  },
  "results": [
    {
      "case_id": "11111111-1111-1111-1111-111111111111",
      "case_no": "2021다12345",
      "court_name": "대법원",
      "court_level": "supreme",
      "decision_date": "2022-03-15",
      "case_name": "손해배상",
      "case_type": "민사",
      "legal_domain": "손해배상",
      "summary_card": "피해자 행위와 과실상계 비율이 핵심 쟁점인 사안입니다.",
      "outcome": {
        "disposition": "일부 인용",
        "direction": "원고 일부 유리",
        "claim_result": "일부 인용",
        "key_factor": "피해자 과실"
      },
      "cited_articles": ["민법_제750조", "민법_제396조"],
      "score": 0.88,
      "evidence_ids": ["p12", "p18"],
      "source_url": "https://www.law.go.kr/precInfoP.do?precSeq=000000",
      "review_status": "pending",
      "confidence_score": 0.82
    }
  ]
}
```

낮은 confidence 응답:

```json
{
  "parsed_intent": {
    "confidence": 0.45,
    "needs_clarification": true,
    "clarification_question": "사고 유형이나 문제된 손해 항목을 한 가지 더 입력해 주세요."
  },
  "search_method": "hybrid_rag",
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 0,
    "has_next": false
  },
  "results": []
}
```

## 7. 사건번호 검색

```http
POST /api/v1/search/case-no
```

요청:

```json
{
  "case_no": "2021다12345"
}
```

응답 fixture:

```json
{
  "results": [
    {
      "case_id": "11111111-1111-1111-1111-111111111111",
      "case_no": "2021다12345",
      "court_name": "대법원",
      "court_level": "supreme",
      "decision_date": "2022-03-15",
      "case_name": "손해배상",
      "case_type": "민사",
      "legal_domain": "손해배상",
      "summary_card": "사건번호로 조회된 판례입니다.",
      "outcome": {
        "disposition": "일부 인용",
        "direction": "원고 일부 유리",
        "claim_result": "일부 인용",
        "key_factor": "피해자 과실"
      },
      "cited_articles": ["민법_제750조"],
      "score": 1.0,
      "evidence_ids": ["p12"],
      "source_url": "https://www.law.go.kr/precInfoP.do?precSeq=000000",
      "review_status": "pending",
      "confidence_score": 0.82
    }
  ]
}
```

## 8. 판례 상세

```http
GET /api/v1/cases/{case_id}
```

응답 fixture:

```json
{
  "case": {
    "case_id": "11111111-1111-1111-1111-111111111111",
    "external_id": "000000",
    "case_no": "2021다12345",
    "court_name": "대법원",
    "court_level": "supreme",
    "decision_date": "2022-03-15",
    "case_name": "손해배상",
    "case_type": "민사",
    "legal_domain": "손해배상",
    "source_url": "https://www.law.go.kr/precInfoP.do?precSeq=000000",
    "collected_at": "2026-06-03T16:41:00+09:00"
  },
  "structure": {
    "facts": "차량 대 보행자 사고에서 전방주시 의무와 피해자 행위가 다투어진 사안입니다.",
    "legal_issue": "불법행위 책임과 과실상계 비율",
    "court_reasoning": "법원은 가해자의 주의의무 위반과 피해자 과실을 함께 고려했습니다.",
    "conclusion": "원고 일부 승소",
    "material_facts": {
      "accident_type": "차량 대 보행자",
      "victim_status": "보행자",
      "defendant_conduct": "전방주시 태만",
      "victim_conduct": "무단횡단 다툼",
      "injury_type": "신체 상해",
      "causation_dispute": true,
      "negligence_offset_issue": true
    },
    "outcome": {
      "disposition": "일부 인용",
      "direction": "원고 일부 유리",
      "claim_result": "일부 인용",
      "key_factor": "피해자 과실",
      "confidence": 0.82
    },
    "cited_articles": ["민법_제750조", "민법_제396조"],
    "facets": {
      "legal_domain": "손해배상",
      "case_type": "민사",
      "harm_type": "신체",
      "court_level": "대법원"
    },
    "evidence_spans": {
      "facts": ["p12"],
      "legal_issue": ["p18"],
      "outcome": ["p24"]
    },
    "confidence_score": 0.82,
    "review_status": "pending"
  },
  "paragraphs": [
    {
      "evidence_id": "p12",
      "paragraph_id": "22222222-2222-2222-2222-222222222222",
      "section_type": "facts",
      "paragraph_order": 12,
      "text": "원문 근거 문단 일부입니다.",
      "char_start": 1200,
      "char_end": 1450
    }
  ]
}
```

## 9. 비교 후보

```http
GET /api/v1/cases/{case_id}/compare-candidates?limit=5&require_outcome_difference=true
```

응답 fixture:

```json
{
  "base_case": {
    "case_id": "11111111-1111-1111-1111-111111111111",
    "case_no": "2021다12345",
    "summary_card": "피해자 과실이 손해배상 범위에서 문제된 기준 판례입니다.",
    "material_facts": {
      "accident_type": "차량 대 보행자",
      "victim_conduct": "무단횡단 다툼",
      "negligence_offset_issue": true
    }
  },
  "ranking_policy": {
    "policy_name": "Set B: 균형형",
    "outcome_difference_weight": 0.03
  },
  "candidates": [
    {
      "case_id": "33333333-3333-3333-3333-333333333333",
      "case_no": "2020다54321",
      "court_name": "대법원",
      "decision_date": "2021-11-10",
      "case_name": "손해배상",
      "summary_card": "유사한 교통사고 사안에서 피해자 과실을 더 높게 본 판례입니다.",
      "scores": {
        "facts_vector_similarity": 0.87,
        "material_fact_match": 0.82,
        "event_structure_match": 0.8,
        "issue_similarity": 0.79,
        "statute_overlap": 0.72,
        "domain_match_score": 1.0,
        "issue_tag_overlap": 0.8,
        "facet_match_score": 0.9,
        "outcome_difference": 1.0,
        "final_score": 0.84
      },
      "match_reasons": [
        "same primary legal domain: damages",
        "shared issue tags: negligence, causation",
        "similar material fact structure"
      ],
      "caution_reasons": [],
      "common_facts": ["차량 대 보행자 사고", "피해자 과실 여부 다툼"],
      "possible_turning_points": ["무단횡단 인정 여부", "운전자 주의의무 정도"],
      "outcome_difference_summary": "기준 판례는 피해자 과실을 낮게 보았고, 후보 판례는 과실상계를 더 크게 인정했습니다.",
      "relaxation_level": 0,
      "evidence_ids": ["p08", "p17"]
    }
  ]
}
```

후보 부족 응답:

```json
{
  "base_case": {
    "case_id": "11111111-1111-1111-1111-111111111111"
  },
  "ranking_policy": {
    "policy_name": "Set B: 균형형",
    "outcome_difference_weight": 0.03
  },
  "candidates": [],
  "relaxation_attempts": [
    {
      "level": 1,
      "description": "같은 법률 도메인과 높은 material fact match로 완화",
      "result_count": 0
    }
  ]
}
```

## 10. 판례 비교 분석

```http
POST /api/v1/compare
```

요청:

```json
{
  "base_case_id": "11111111-1111-1111-1111-111111111111",
  "compare_case_id": "33333333-3333-3333-3333-333333333333"
}
```

응답 fixture:

```json
{
  "base": {
    "case_id": "11111111-1111-1111-1111-111111111111",
    "case_no": "2021다12345",
    "court_name": "대법원",
    "decision_date": "2022-03-15",
    "outcome": {
      "direction": "원고 일부 유리",
      "key_factor": "피해자 과실"
    }
  },
  "compare": {
    "case_id": "33333333-3333-3333-3333-333333333333",
    "case_no": "2020다54321",
    "court_name": "대법원",
    "decision_date": "2021-11-10",
    "outcome": {
      "direction": "원고 청구 감액",
      "key_factor": "무단횡단"
    }
  },
  "analysis": {
    "common_points": [
      {
        "text": "두 판례 모두 차량 대 보행자 사고에서 손해배상 범위와 과실상계가 문제되었습니다.",
        "evidence_ids": {
          "base": ["p12"],
          "compare": ["p08"]
        }
      }
    ],
    "material_differences": [
      {
        "factor": "피해자 행위",
        "base": "피해자 과실을 낮게 보았습니다.",
        "compare": "무단횡단을 과실상계 사유로 크게 보았습니다.",
        "meaning": "피해자 행위 인정 정도가 과실상계 비율을 가른 분기점일 수 있습니다.",
        "evidence_ids": {
          "base": ["p21"],
          "compare": ["p17"]
        }
      }
    ],
    "turning_points": [
      {
        "title": "무단횡단 인정 여부",
        "explanation": "사실관계는 유사하지만 피해자 행위 평가가 달라 결과가 달라졌을 가능성이 있습니다.",
        "evidence_ids": {
          "base": ["p21"],
          "compare": ["p17"]
        }
      }
    ],
    "result_difference": "기준 판례는 일부 인용, 비교 판례는 과실상계를 더 크게 반영한 감액 방향입니다.",
    "generated_by": "llm",
    "fallback_used": false
  },
  "evidence_links": {
    "base": [
      {
        "evidence_id": "p21",
        "section_type": "reasoning",
        "text": "기준 판례 원문 근거 문단입니다."
      }
    ],
    "compare": [
      {
        "evidence_id": "p17",
        "section_type": "reasoning",
        "text": "비교 판례 원문 근거 문단입니다."
      }
    ]
  },
  "disclaimer": "CaseLens의 비교 분석은 참고용 정보이며 법률 판단을 대체하지 않습니다."
}
```

LLM timeout fallback:

```json
{
  "analysis": {
    "common_points": [],
    "material_differences": [],
    "turning_points": [],
    "result_difference": "구조화 데이터 기준 결과 차이만 표시합니다.",
    "generated_by": "structured_fallback",
    "fallback_used": true,
    "fallback_reason": "LLM_TIMEOUT"
  },
  "evidence_links": {},
  "disclaimer": "CaseLens의 비교 분석은 참고용 정보이며 법률 판단을 대체하지 않습니다."
}
```

## 11. 피드백

```http
POST /api/v1/feedback
```

요청:

```json
{
  "query_id": "44444444-4444-4444-4444-444444444444",
  "base_case_id": "11111111-1111-1111-1111-111111111111",
  "compare_case_id": "33333333-3333-3333-3333-333333333333",
  "label": "facts_not_similar",
  "reason": "사고 유형은 같지만 피해자 행위가 너무 다릅니다.",
  "comment": "비교 후보로 보기 어렵습니다."
}
```

응답:

```json
{
  "feedback_id": "55555555-5555-5555-5555-555555555555",
  "status": "saved"
}
```

허용 label:

```text
relevant
not_relevant
facts_not_similar
material_fact_missed
wrong_statute
outcome_not_different
summary_error
source_needed
```

## 12. 수집 API 응답과 내부 DB 매핑 메모

법령정보센터 API 응답은 수집 단계에서 다음 내부 필드로 매핑한다.

```text
판례 목록/상세
→ cases.external_id
→ cases.case_no
→ cases.court_name
→ cases.decision_date
→ cases.case_name
→ cases.raw_text/raw_html
→ cases.source_url

법령/조문
→ laws.law_code
→ laws.official_name
→ laws.short_name
→ articles.article_no
→ articles.title
→ articles.body
→ articles.normalized_ref
```

런타임 API는 위 내부 테이블만 조회한다.

## 13. 구현 완료 체크리스트

- [ ] 프론트엔드 mock fixture가 이 문서와 같은 형태로 작성되어 있다.
- [ ] FastAPI schema가 이 문서의 요청/응답과 일치한다.
- [ ] 조문 검색은 내부 `articles.normalized_ref` 검증을 통과해야 한다.
- [ ] 비교 후보 점수에서 outcome difference 비중은 0.03으로 유지된다.
- [ ] 비교 분석의 모든 주장에는 evidence id가 있거나 근거 부족 표시가 있다.
