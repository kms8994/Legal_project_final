# MVP Evaluation Set

## 1. Purpose

This file defines the first CaseLens MVP evaluation set. The goal is not to produce a final legal-quality benchmark yet, but to make search and comparison quality measurable after the 300-case data load.

Evaluation has two layers:

1. Automatic first pass: `npm.cmd run eval:mvp`
2. Manual review: inspect the generated Top results and mark whether the automatic heuristic was correct.

Generated outputs:

- `docs/evaluation_run.json`
- `docs/EvaluationRun.md`

## 2. Statute Search Set

Metric:

- `precision@10`: result is relevant when `expected_ref` is present in `cited_articles`.
- `in-scope precision@10`: same metric, but excludes rows marked `missing_scope`.
- `top1 exact article rate`: first result cites the expected article.
- `scope_status`: `in_scope` means the current DB should support the query; `missing_scope` means it is useful for future expansion but should not be treated as a current logic failure.

| ID | Query | Expected Ref | Scope | Intent |
|----|-------|--------------|-------|--------|
| S01 | 민법 제750조 | 민법_제750조 | in_scope | 불법행위 손해배상 일반 |
| S02 | 민법 제751조 | 민법_제751조 | in_scope | 위자료 및 정신적 손해 |
| S03 | 민법 제396조 | 민법_제396조 | in_scope | 과실상계 |
| S04 | 민법 제393조 | 민법_제393조 | in_scope | 손해배상 범위 |
| S05 | 민법 제763조 | 민법_제763조 | in_scope | 불법행위 손해배상 준용 |
| S06 | 민법 제766조 | 민법_제766조 | in_scope | 손해배상청구권 소멸시효 |
| S07 | 민법 제756조 | 민법_제756조 | missing_scope | 사용자책임 |
| S08 | 민법 제760조 | 민법_제760조 | missing_scope | 공동불법행위 |
| S09 | 민법 750 | 민법_제750조 | in_scope | 약식 조문 입력 정규화 |
| S10 | 자동차손해배상 보장법 제3조 | 자동차손해배상 보장법_제3조 | in_scope | 자동차 사고 손해배상 책임 |

## 3. Natural Search Set

Automatic relevance is a heuristic. A Top-5 result is counted relevant if it has either:

- an expected article in `cited_articles`
- enough expected terms in the case title, summary, cited articles, outcome, or evidence snippets

Manual review should override the heuristic when the result is keyword-matched but legally off-topic.

| ID | Query | Expected Terms | Expected Articles | Intent |
|----|-------|----------------|-------------------|--------|
| N01 | 교통사고 피해자의 무단횡단과 과실상계가 문제된 손해배상 판례 | 교통사고, 무단횡단, 과실상계, 손해배상 | 민법_제396조, 민법_제750조 | 교통사고 과실상계 |
| N02 | 운전자가 전방주시의무를 위반해 보행자를 다치게 한 사건 | 전방주시, 보행자, 교통사고, 과실 | 민법_제750조 | 운전자 주의의무 위반 |
| N03 | 자동차 운행자 책임과 보험자의 손해배상 책임이 문제된 판례 | 자동차, 운행자, 보험, 손해배상 | 자동차손해배상 보장법_제3조 | 자동차손해배상 보장법 책임 |
| N04 | 피해자에게도 일부 잘못이 있어 배상액이 줄어든 사건 | 피해자, 과실, 배상액, 감액 | 민법_제396조 | 피해자 과실과 감액 |
| N05 | 위자료 액수가 어떻게 정해지는지 문제된 손해배상 판례 | 위자료, 정신적, 손해, 배상 | 민법_제751조 | 위자료 산정 |
| N06 | 회사 직원이 업무 중 사고를 내서 사용자 책임이 문제된 사건 | 회사, 직원, 업무, 사용자책임 | 민법_제756조 | 사용자책임 |
| N07 | 여러 사람이 함께 손해를 발생시킨 공동불법행위 판례 | 공동, 불법행위, 손해, 여러 | 민법_제760조 | 공동불법행위 |
| N08 | 사고와 손해 사이의 인과관계가 다투어진 판례 | 사고, 손해, 인과관계 | 민법_제750조 | 인과관계 |
| N09 | 손해배상청구권 소멸시효가 문제된 판례 | 손해배상청구권, 소멸시효 | 민법_제766조 | 소멸시효 |
| N10 | 통상손해와 특별손해의 배상 범위가 문제된 판례 | 통상손해, 특별손해, 배상, 범위 | 민법_제393조 | 손해배상 범위 |

## 4. Compare Candidate Set

The first automatic compare evaluation uses the top natural-search result from each natural query as a base case. For each base case, it requests five candidates with `require_outcome_difference=false`.

Automatic metrics:

- average `material_fact_match`
- average `facts_vector_similarity`
- average `issue_similarity`
- evidence coverage rate

Manual labels should score each candidate from 0 to 2.

| Label | 0 | 1 | 2 |
|-------|---|---|---|
| fact similarity | 사실관계 다름 | 일부 유사 | 핵심 사건 구조 유사 |
| material fact match | 중요 사실 다름 | 일부 일치 | 대부분 일치 |
| issue similarity | 쟁점 다름 | 관련 있음 | 같은 쟁점 |
| outcome difference | 차이 없음 | 약한 차이 | 뚜렷한 차이 |
| turning point clarity | 설명 불가 | 추정 가능 | 근거로 설명 가능 |
| evidence coverage | 근거 없음 | 일부 근거 | 충분한 근거 |

Good candidate threshold:

```text
fact similarity >= 1
material fact match >= 1
issue similarity >= 1
turning point clarity >= 1
```

Strong candidate threshold:

```text
fact similarity = 2
material fact match = 2
issue similarity >= 1
outcome difference >= 1
evidence coverage >= 1
```

## 5. MVP Gates

Initial warning gates:

| Area | Warning Condition |
|------|-------------------|
| Statute search | precision@10 < 0.70 |
| Natural search | average Top-5 relevant count < 3 |
| Compare candidates | average material fact match < 0.30 |
| Structure validation | needs_review rate > 0.50 |
| API latency | p95 > 4 seconds |

These gates are warnings, not release blockers. They identify where the next iteration should focus.
