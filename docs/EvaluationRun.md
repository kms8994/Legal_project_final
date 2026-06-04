# MVP Evaluation Run

- Generated at: `2026-06-05T02:57:06`
- Labeling mode: heuristic first pass. Use top results below for manual confirmation.

## Summary

| Area | Metric | Value |
|------|--------|-------|
| Statute search | precision@10 | 0.6 |
| Statute search | top1 exact article rate | 0.6 |
| Natural search | avg Top-5 relevant count | 1.9 |
| Compare candidates | avg material fact match | 0.7 |
| Compare candidates | evidence coverage rate | 0.0 |
| Structure validation | needs_review rate | 0.77 |

## DB Snapshot

- Cases: 221
- Paragraphs: 35470
- Structures: 226
- Embeddings: 1034
- Review status: `{"auto_validated": 52, "needs_review": 174}`

## Statute Search

| ID | Query | Expected | Status | P@10 | First Hit | Top Result |
|----|-------|----------|--------|------|-----------|------------|
| S01 | 민법 제750조 | 민법_제750조 | 200 | 1.0 | 1 | 2025나10683 |
| S02 | 민법 제751조 | 민법_제751조 | 200 | 1.0 | 1 | 2014다61654 |
| S03 | 민법 제396조 | 민법_제396조 | 200 | 1.0 | 1 | 2024가단100001 |
| S04 | 민법 제393조 | 민법_제393조 | 200 | 1.0 | 1 | 2020나2034989 |
| S05 | 민법 제763조 | 민법_제763조 | 200 | 1.0 | 1 | 2019다236385 |
| S06 | 민법 제766조 | 민법_제766조 | 200 | 1.0 | 1 | 2021다213477 |
| S07 | 민법 제756조 | 민법_제756조 | 404 | 0.0 | None |  |
| S08 | 민법 제760조 | 민법_제760조 | 404 | 0.0 | None |  |
| S09 | 민법 750 | 민법_제750조 | 400 | 0.0 | None |  |
| S10 | 자동차손해배상 보장법 제3조 | 자동차손해배상_보장법_제3조 | 200 | 0.0 | None | 2019가단5248886 |

## Natural Search

| ID | Query | Status | Top-5 Relevant | Top Result |
|----|-------|--------|----------------|------------|
| N01 | 교통사고 피해자의 무단횡단과 과실상계가 문제된 손해배상 판례 | 200 | 4 | 2024가단100001 |
| N02 | 운전자가 전방주시의무를 위반해 보행자를 다치게 한 사건 | 200 | 4 | 2019가단5248886 |
| N03 | 자동차 운행자 책임과 보험자의 손해배상 책임이 문제된 판례 | 200 | 1 | 2019가단5248886 |
| N04 | 피해자에게도 일부 잘못이 있어 배상액이 줄어든 사건 | 200 | 0 | 2020나62251 |
| N05 | 위자료 액수가 어떻게 정해지는지 문제된 손해배상 판례 | 200 | 4 | 2023나100002 |
| N06 | 회사 직원이 업무 중 사고를 내서 사용자 책임이 문제된 사건 | 200 | 0 | 2020나62251 |
| N07 | 여러 사람이 함께 손해를 발생시킨 공동불법행위 판례 | 200 | 0 | 2017나2055054 |
| N08 | 사고와 손해 사이의 인과관계가 다투어진 판례 | 200 | 5 | 2020나60108 |
| N09 | 손해배상청구권 소멸시효가 문제된 판례 | 200 | 0 | 2024다239364 |
| N10 | 통상손해와 특별손해의 배상 범위가 문제된 판례 | 200 | 1 | 2024다239364 |

## Compare Candidates

| Base Case | Status | Candidates | Top Candidate | Top Material Match |
|-----------|--------|------------|---------------|--------------------|
| 1c9d125f-dff1-41a6-ac46-64a2ac905416 | 200 | 5 | 2019가합40778 | 0.6 |
| 72083798-a010-484f-92f8-73c2cb13afa4 | 200 | 5 | 2020나60108 | 0.9 |
| b9dffc39-c646-415d-ad71-4a605cd88634 | 200 | 5 | 2020나64837 | 0.8 |
| fd661a4a-c991-47cf-ad15-c9b22f7cdc43 | 200 | 5 | 2021르6860(본소), 2022르5482(반소) | 0.9 |
| d95a8e66-380b-480e-b437-5ad441d6c609 | 200 | 5 | 2020가합101417 | 0.6 |
| c57a37b4-b9f1-4312-9e96-4d0283bf39c0 | 200 | 5 | 2014가합62810 | 0.7 |
| b33805ae-e911-47df-b8c6-e3cb70948a35 | 200 | 5 | 2016다34007 | 0.9 |

## Next Manual Checks

- Confirm whether each natural-search Top-5 result is actually relevant, not only keyword-matched.
- Inspect 20 `needs_review` structures and classify the failure reason.
- Review compare candidates with high vector similarity but low material fact match.

Full machine-readable output is in `docs/evaluation_run.json`.
