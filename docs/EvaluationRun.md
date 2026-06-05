# MVP Evaluation Run

- Generated at: `2026-06-05T20:10:30`
- Labeling mode: heuristic first pass. Use top results below for manual confirmation.

## Summary

| Area | Metric | Value |
|------|--------|-------|
| Statute search | precision@10 | 1.0 |
| Statute search | in-scope precision@10 | 1.0 |
| Statute search | top1 exact article rate | 1.0 |
| Natural search | avg Top-5 relevant count | 3.625 |
| Natural search | avg Top-5 MVP relevant count | 3.312 |
| Natural search | avg Top-5 domain relevant count | 5 |
| Compare candidates | avg material fact match | 0.836 |
| Compare candidates | avg domain match score | 1.0 |
| Compare candidates | avg issue tag overlap | 0.778 |
| Compare candidates | evidence coverage rate | 1.0 |
| Structure validation | needs_review rate | 0.607 |
| Structure validation | true quality issue rate | 0.126 |
| Structure validation | missing scope rate | 0.293 |
| Structure validation | out-of-scope rate | 0.396 |
| Structure validation | low confidence rate | 0.154 |
| Structure validation | primary quality issue rate | 0.061 |
| Structure validation | primary missing scope rate | 0.18 |
| Structure validation | primary out-of-scope rate | 0.367 |
| Structure validation | primary low confidence rate | 0.0 |
| MVP relevance | mvp_relevant rate | 0.416 |
| MVP relevance | weakly_related rate | 0.121 |
| MVP relevance | out_of_scope rate | 0.463 |

## DB Snapshot

- Cases: 1076
- Paragraphs: 119542
- Structures: 1075
- Embeddings: 9267
- Review status: `{"auto_validated": 422, "needs_review": 653}`
- Review categories: `{"low_confidence": 166, "missing_scope": 315, "out_of_scope": 426, "quality_issue": 135}`
- Primary review categories: `{"auto_validated": 422, "missing_scope": 193, "out_of_scope": 394, "quality_issue": 66}`
- MVP relevance: `{"mvp_relevant": 447, "out_of_scope": 498, "weakly_related": 130}`
- Primary domains: `{"damages": 532, "labor": 114, "unjust_enrichment": 94, "lease": 86, "tax": 81, "property": 53, "inheritance": 49, "family": 26, "contract": 24, "insurance": 9, "ip": 5, "general": 2}`

## Statute Search

| ID | Query | Expected | Scope | Status | P@10 | First Hit | Top Result |
|----|-------|----------|-------|--------|------|-----------|------------|
| S01 | 민법 제750조 | 민법_제750조 | in_scope | 200 | 1.0 | 1 | 2024나2013287 |
| S02 | 민법 제751조 | 민법_제751조 | in_scope | 200 | 1.0 | 1 | 2025다200820 |
| S03 | 민법 제396조 | 민법_제396조 | in_scope | 200 | 1.0 | 1 | 2024나2023710 |
| S04 | 민법 제393조 | 민법_제393조 | in_scope | 200 | 1.0 | 1 | 2019다236385 |
| S05 | 민법 제763조 | 민법_제763조 | in_scope | 200 | 1.0 | 1 | 2019다236385 |
| S06 | 민법 제766조 | 민법_제766조 | in_scope | 200 | 1.0 | 1 | 2024나2013287 |
| S07 | 민법 제756조 | 민법_제756조 | missing_scope | 200 | 1.0 | 1 | 2023나2013051 |
| S08 | 민법 제760조 | 민법_제760조 | missing_scope | 200 | 1.0 | 1 | 2023구단50168 |
| S09 | 민법 750 | 민법_제750조 | in_scope | 200 | 1.0 | 1 | 2024나2013287 |
| S10 | 자동차손해배상 보장법 제3조 | 자동차손해배상 보장법_제3조 | in_scope | 200 | 1.0 | 1 | 2023다231738 |

## Natural Search

| ID | Query | Expected Domain | Status | Top-5 Relevant | Top Result | Top Domain |
|----|-------|-----------------|--------|----------------|------------|------------|
| N01 | 교통사고 피해자의 무단횡단과 과실상계가 문제된 손해배상 판례 |  | 200 | 5 / MVP 5 / Domain 5 | 2022다235009 | damages / insurance |
| N02 | 운전자가 전방주시의무를 위반해 보행자를 다치게 한 사건 |  | 200 | 2 / MVP 5 / Domain 5 | 2019가단5111656 | damages / insurance,unjust_enrichment |
| N03 | 자동차 운행자 책임과 보험자의 손해배상 책임이 문제된 판례 |  | 200 | 4 / MVP 5 / Domain 5 | 2024다238217 | damages / unjust_enrichment,insurance |
| N04 | 피해자에게도 일부 잘못이 있어 배상액이 줄어든 사건 |  | 200 | 5 / MVP 4 / Domain 5 | 2024나7566 | damages / insurance |
| N05 | 위자료 액수가 어떻게 정해지는지 문제된 손해배상 판례 |  | 200 | 5 / MVP 5 / Domain 5 | 2020나2012804, 2020나2012811(병합), 2020나2012828(병합) | damages / tax |
| N06 | 회사 직원이 업무 중 사고를 내서 사용자 책임이 문제된 사건 |  | 200 | 5 / MVP 5 / Domain 5 | 2020가단5024659 | damages / insurance,lease,tax,contract |
| N07 | 여러 사람이 함께 손해를 발생시킨 공동불법행위 판례 |  | 200 | 5 / MVP 5 / Domain 5 | 2022나17283 | damages / insurance,unjust_enrichment |
| N08 | 사고와 손해 사이의 인과관계가 다투어진 판례 |  | 200 | 1 / MVP 5 / Domain 5 | 2011나31415 | damages / insurance,contract |
| N09 | 손해배상청구권 소멸시효가 문제된 판례 |  | 200 | 5 / MVP 5 / Domain 5 | 2024나2061118 | damages |
| N10 | 통상손해와 특별손해의 배상 범위가 문제된 판례 |  | 200 | 5 / MVP 5 / Domain 5 | 2019다236385 | damages / contract |
| G01 | 임대차보증금 반환이 문제된 판례 | lease | 200 | 4 / MVP 0 / Domain 5 | 88나4472 | lease / damages,property |
| G02 | 계약대금 지급과 채무불이행이 문제된 판례 | contract | 200 | 2 / MVP 1 / Domain 5 | 2025다209893, 209894 | contract / damages,lease,tax,property |
| G03 | 부당이득 반환청구 판례 | unjust_enrichment | 200 | 2 / MVP 0 / Domain 5 | 2022나47508 | unjust_enrichment / damages,contract |
| G04 | 근로자 임금 퇴직금 청구 판례 | labor | 200 | 2 / MVP 0 / Domain 5 | 2013가합11648 | labor |
| G05 | 상속재산 분할과 유류분 반환이 문제된 판례 | inheritance | 200 | 2 / MVP 1 / Domain 5 | 2018가합114335 | inheritance / damages,unjust_enrichment,lease,tax,property,contract,family |
| G06 | 취득세 부과처분 취소 판례 | tax | 200 | 4 / MVP 2 / Domain 5 | 2020구합51994 | tax / damages,lease,property,ip,contract |

## Compare Candidates

| Base Case | Status | Candidates | Top Candidate | Top Material Match | Domain Match | Issue Tags |
|-----------|--------|------------|---------------|--------------------|--------------|------------|
| b4c08f2b-7421-4b45-b445-e9b31e72bb24 | 200 | 5 | 2020나60108 | 0.8 | 1.0 | 1.0 |
| e8962fec-9888-433c-baa0-a92765fafeda | 200 | 5 | 2007다89494 | 0.8 | 1.0 | 0.75 |
| 337556fe-c38a-4ad8-ae92-15483be2abe7 | 200 | 5 | 2019다208687 | 1.0 | 1.0 | 0.75 |
| ffd2991f-329d-4036-9b0b-b61bad5c667f | 200 | 5 | 2011나14379 | 0.9 | 1.0 | 1.0 |
| 34ac3b4f-4462-4dd0-916c-ee46b15249eb | 200 | 5 | 2019나51126 | 0.8 | 1.0 | 1.0 |
| 3f1e3985-b251-43a3-aee4-4fd92e82a218 | 200 | 5 | 2023나18356 | 0.9 | 1.0 | 0.571 |
| 4205d2d3-9ad4-411d-a695-f8c9fc4fe455 | 200 | 5 | 2020가합402887 | 0.7 | 1.0 | 0.8 |
| 43800b01-b816-43e0-bd0d-faacda374ef1 | 200 | 5 | 2018가합30217 | 0.8 | 1.0 | 0.625 |
| 6865850e-c5fc-47dd-aec0-31476dd708a8 | 200 | 5 | 84나511 | 0.9 | 1.0 | 0.429 |
| 71858010-ef99-4702-b7e8-7e7b3d280bc9 | 200 | 5 | 2021나82847 | 0.8 | 1.0 | 1.0 |

## Next Manual Checks

- Confirm whether each natural-search Top-5 result is actually relevant, not only keyword-matched.
- Inspect 20 `needs_review` structures and classify the failure reason.
- Review compare candidates with high vector similarity but low material fact match.

Full machine-readable output is in `docs/evaluation_run.json`.
