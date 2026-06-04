# Needs Review Analysis

## 1. Snapshot

Generated on 2026-06-05 after the 300-case pipeline run and flexible article normalization work.

Current DB review status:

| Status | Count |
|--------|-------|
| auto_validated | 52 |
| needs_review | 174 |

Top validation reasons across 174 `needs_review` structures:

| Reason | Count | Interpretation |
|--------|-------|----------------|
| confidence_below_threshold | 123 | Structure has some useful data, but confidence scoring is low. |
| legal_domain_unknown | 52 | Case is likely outside the damages MVP scope or damages keywords were not detected. |
| cited_articles_empty | 34 | No statute citation was extracted. |
| cited_article_unknown:민법_제756조 | 15 | Valid future-scope statute, not currently in `articles`. |
| cited_article_unknown:민법_제760조 | 11 | Valid future-scope statute, not currently in `articles`. |
| cited_article_unknown:민법_제758조 | 10 | Related tort statute, not currently in `articles`. |
| outcome_direction_unknown | 7 | Outcome extraction found no direction. |
| outcome_disposition_unknown | 7 | Outcome extraction found no disposition. |
| cited_articles_evidence_missing | 3 | Citation exists but evidence span is missing. |
| outcome_evidence_missing | 1 | Outcome exists but evidence span is missing. |

## 2. Sample Findings

20 recent `needs_review` rows were inspected with case metadata, validation reasons, structured fields, evidence keys, and raw text preview.

Observed categories:

| Category | Examples | Meaning |
|----------|----------|---------|
| Future-scope statute | 민법 제756조, 제760조, 제758조, 제35조, 제548조 | The extractor found real citations, but current MVP article DB does not include them. |
| Out-of-domain case | 취득세, 상속, 토지인도, 근저당권, 이혼 | Collected data includes cases that cite civil-law provisions but are not damages-learning targets. |
| Seed/sample text without explicit citation | 2024가단100001, 2023나100002, 2022가단100003 | The sample text describes liability but does not contain explicit `민법 제...조`, so citation extraction fails. |
| Confidence scoring too punitive | Several rows have outcome/domain/evidence but still score below threshold | Validation treats unknown article refs and missing citations as hard quality problems. |
| Evidence span gap | cited_articles_evidence_missing, outcome_evidence_missing | Relatively rare after evidence id extraction fix. |

## 3. Root Cause

The high `needs_review` rate is not one single bug.

Main causes:

1. Current article DB is intentionally narrow.
   - Many extracted citations are real but outside MVP P0/P1 article rows.
   - These should be classified as `missing_scope`, not necessarily poor extraction.

2. Collected cases include non-damages or weakly related cases.
   - Some cases are tax, inheritance, property, lease, mortgage, or family-law disputes.
   - They should be stored but ranked lower or excluded from MVP evaluation.

3. Rule-based extraction expects explicit legal citation text.
   - Handwritten seed/sample cases often say "불법행위책임" or "위자료" without citing `민법 제750조` or `민법 제751조`.
   - Humans understand the legal basis, but the rule extractor does not infer citations from concepts yet.

4. Confidence scoring mixes data scope with structure quality.
   - Unknown article in current DB lowers review status even when the extracted citation is valid in the broader law.
   - This makes `needs_review` look worse than actual parser quality.

## 4. Recommended Fix Order

Do not expand data collection first. Fix classification and validation semantics first.

1. Split review reasons into `quality_issue` and `scope_issue`.
   - `cited_article_unknown:*` should become `missing_scope` when the article ref is syntactically valid but absent from current MVP DB.
   - This will separate future data expansion from parser failure.

2. Add MVP relevance status.
   - Use values like `mvp_relevant`, `weakly_related`, `out_of_scope`.
   - Cases with `legal_domain_unknown` and non-damages titles should not count against core search quality.

3. Add citation inference only for high-confidence concepts.
   - Example: if text contains `불법행위책임` and damages terms, infer `민법_제750조` with lower confidence.
   - Example: if text contains `위자료` or `정신적 고통`, infer `민법_제751조`.
   - Keep inferred citations marked separately from explicit citations.

4. Adjust confidence calculation.
   - Do not treat `missing_scope` the same as extraction failure.
   - Give useful structures a searchable status even if they still need admin review.

5. Re-run validation and evaluation.
   - Target: lower true quality-related `needs_review` without hiding future-scope or out-of-domain cases.

## 5. Next Concrete Step

Implement review classification in validation output:

```text
review_status:
  auto_validated
  needs_review
  invalid

review_category:
  quality_issue
  scope_issue
  out_of_scope
  low_confidence
```

Short-term target:

```text
needs_review remains visible, but evaluation reports:
- true quality issue rate
- missing scope rate
- out-of-scope rate
```

This gives a fairer signal before expanding the DB.
