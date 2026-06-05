# Needs Review Analysis

## 13. General-Domain Retrieval and Compare Ranking

Implemented on 2026-06-05.

The service direction changed from damages-only relevance filtering to general legal-domain retrieval. The new rule is:

- All collected cases remain searchable.
- `mvp_relevance` is retained only as a damages-query auxiliary signal.
- General ranking uses `primary_domain`, `secondary_domains`, and `issue_tags`.
- Compare candidates now rank by legal-domain match and issue-tag overlap in addition to material facts, statute overlap, vector similarity, and outcome difference.

Search-facing structure now exposes:

- `primary_domain`
- `secondary_domains`
- `issue_tags`
- `mvp_relevance`

Compare candidate scoring now includes:

- `domain_match_score`
- `issue_tag_overlap`
- `facet_match_score`

Current primary domain distribution from the latest evaluation snapshot:

| Domain | Count |
|--------|-------|
| damages | 325 |
| unjust_enrichment | 24 |
| lease | 20 |
| labor | 18 |
| contract | 11 |
| family | 10 |
| tax | 9 |
| property | 9 |
| inheritance | 7 |
| insurance | 6 |
| ip | 4 |
| general | 2 |

Validation:

```powershell
npm.cmd run api:test
```

Result: 50 passed.

Next data step:

- Expand non-damages domains deliberately instead of adding more damages-only cases.
- Add evaluation queries for contract, lease, labor, inheritance, tax, property, insurance, unjust enrichment, and family cases.
- Re-run structure/validate/embed/eval after each domain batch to check whether compare candidates stay within the same legal domain and issue family.

## 14. General-Domain Data Expansion Result

Implemented on 2026-06-05.

Added six small non-damages collection batches:

```powershell
npm.cmd run collect:cases -- --scope general --query "임대차보증금 반환" --limit 40 --display 40 --max-pages 1
npm.cmd run collect:cases -- --scope general --query "계약대금 채무불이행" --limit 40 --display 40 --max-pages 1
npm.cmd run collect:cases -- --scope general --query "부당이득 반환청구" --limit 40 --display 40 --max-pages 1
npm.cmd run collect:cases -- --scope general --query "근로자 임금 퇴직금" --limit 40 --display 40 --max-pages 1
npm.cmd run collect:cases -- --scope general --query "상속재산 분할 유류분" --limit 40 --display 40 --max-pages 1
npm.cmd run collect:cases -- --scope general --query "취득세 부과처분 취소" --limit 40 --display 40 --max-pages 1
```

Each batch fetched and upserted 40 cases with 0 failed items.

Post-collection pipeline:

```powershell
npm.cmd run pipeline:normalize -- --limit 1000
npm.cmd run pipeline:split -- --limit 300
npm.cmd run pipeline:structure -- --limit 1000 --overwrite
npm.cmd run pipeline:validate -- --limit 1000
npm.cmd run pipeline:embed -- --limit 1000
npm.cmd run eval:mvp
```

Latest primary domain distribution:

| Domain | Count |
|--------|-------|
| damages | 355 |
| unjust_enrichment | 53 |
| tax | 52 |
| labor | 44 |
| lease | 41 |
| contract | 15 |
| inheritance | 14 |
| property | 14 |
| family | 10 |
| insurance | 8 |
| ip | 4 |
| general | 2 |

Latest evaluation highlights:

| Metric | Value |
|--------|-------|
| natural avg Top-5 relevant count | 2.438 |
| natural avg Top-5 domain relevant count | 5 |
| compare avg material fact match | 0.816 |
| compare avg domain match score | 0.958 |
| compare avg issue tag overlap | 0.667 |
| evidence coverage rate | 1.0 |
| needs_review_rate | 0.623 |

Interpretation:

- The DB is no longer damages-only; lease, unjust enrichment, labor, tax, contract, inheritance, and related domains now have explicit coverage.
- Domain-aware retrieval is working strongly at the Top-5 level.
- Some general-domain queries still surface results whose `primary_domain` is damages but whose `secondary_domains` match the requested domain. This is acceptable for recall, but the next ranking improvement should prefer primary-domain matches above secondary-domain matches.
- `needs_review_rate` rose because non-damages statutes are not yet covered in the article scope. This is expected after broadening the domain.

Validation:

```powershell
npm.cmd run api:test
```

Result: 50 passed.

## 15. Primary-Domain Ranking Boost Result

Implemented on 2026-06-05.

Changed natural-search ranking so a query's inferred legal domain is scored differently depending on where it appears:

- `primary_domain` match: strong boost.
- `secondary_domains` match: smaller recall boost.
- no domain match: no domain boost.

This keeps secondary-domain recall but prevents incidental mixed-domain cases from outranking cases whose main legal domain directly matches the user query.

Latest evaluation after the ranking adjustment:

| Metric | Before | After |
|--------|--------|-------|
| natural avg Top-5 relevant count | 2.438 | 2.562 |
| natural avg Top-5 domain relevant count | 5 | 5 |
| compare avg material fact match | 0.816 | 0.830 |
| compare avg domain match score | 0.958 | 0.946 |
| compare avg issue tag overlap | 0.667 | 0.705 |

General-domain Top-1 results now align with the requested primary domain:

| Query ID | Expected Domain | Top Result Domain |
|----------|-----------------|-------------------|
| G01 | lease | lease |
| G02 | contract | contract |
| G03 | unjust_enrichment | unjust_enrichment |
| G04 | labor | labor |
| G05 | inheritance | inheritance |
| G06 | tax | tax |

Validation:

```powershell
npm.cmd run api:test
npm.cmd run eval:mvp
```

Result: 50 tests passed; evaluation report regenerated.

## 16. Compare Candidate Explanation Result

Implemented on 2026-06-05.

Compare candidate responses now include explicit explanation fields:

- `match_reasons`: why the candidate is a good comparison candidate.
- `caution_reasons`: why the candidate may be weaker or should be reviewed carefully.

The generated reasons use structured signals:

- same or related legal domain
- shared issue tags
- similar material fact structure
- overlapping cited articles
- similar legal issue text
- different primary domains
- missing issue-tag overlap
- low material-fact match

Candidate ranking was also adjusted to prefer stronger primary-domain matches over weaker related-domain matches.

Latest evaluation:

| Metric | Value |
|--------|-------|
| natural avg Top-5 relevant count | 2.562 |
| natural avg Top-5 domain relevant count | 5 |
| compare avg material fact match | 0.816 |
| compare avg domain match score | 0.948 |
| compare avg issue tag overlap | 0.687 |

Validation:

```powershell
npm.cmd run api:test
npm.cmd run eval:mvp
```

Result: 50 tests passed; evaluation report regenerated with candidate reasons.

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

## 6. Classification Implementation Result

Implemented on 2026-06-05.

Validation output now stores:

```json
{
  "status": "needs_review",
  "reasons": ["cited_article_unknown:민법_제756조", "confidence_below_threshold"],
  "categories": ["missing_scope", "low_confidence"],
  "primary_category": "missing_scope"
}
```

Re-run command:

```powershell
npm.cmd run pipeline:validate -- --limit 300
npm.cmd run eval:mvp
```

Latest category snapshot:

| Category | Count | Rate |
|----------|-------|------|
| quality_issue | 46 | 0.204 |
| missing_scope | 135 | 0.597 |
| out_of_scope | 52 | 0.230 |
| low_confidence | 174 | 0.770 |

Interpretation:

- The headline `needs_review_rate` remains `0.770`, as expected.
- The true quality issue signal is much lower at `0.204`.
- The largest actionable bucket is `missing_scope`, mostly valid statutes not yet in the MVP article DB.
- The next engineering step should target missing-scope article coverage or out-of-scope filtering before spending more time on extractor rules.

## 7. P1 Article Expansion Result

Implemented on 2026-06-05.

Expanded `articles` DB with P1 damages statutes from `docs/StatuteScope.md`:

| Priority | Article | Topic |
|----------|---------|-------|
| P1 | 민법 제756조 | 사용자책임 |
| P1 | 민법 제760조 | 공동불법행위 |
| P1 | 민법 제758조 | 공작물 책임 |
| P1 | 민법 제755조 | 감독자 책임 |

Command result:

```powershell
npm.cmd run collect:laws -- --priority P0,P1
```

```json
{
  "laws_upserted": 2,
  "aliases_upserted": 5,
  "articles_upserted": 12,
  "failed_items": 0
}
```

Post-expansion evaluation:

| Metric | Before | After |
|--------|--------|-------|
| statute precision@10 | 0.800 | 1.000 |
| in-scope statute precision@10 | 1.000 | 1.000 |
| missing_scope_rate | 0.597 | 0.504 |
| needs_review_rate | 0.770 | 0.770 |
| true_quality_issue_rate | 0.204 | 0.204 |

Interpretation:

- P1 expansion fixed the most obvious missing tort statutes (`민법 제756조`, `제758조`, `제760조`).
- `needs_review_rate` did not drop because low confidence remains attached to the same rows.
- Remaining missing-scope leaders are now broader or mixed-domain provisions such as `민법 제162조`, `제103조`, `제35조`, `제2조`, `제163조`, and `제390조`.
- Next expansion should be selective: add `민법 제35조` and `민법 제390조` if needed for damages coverage, but handle many remaining refs through out-of-scope filtering rather than blindly expanding all civil-code articles.

## 8. Selective Expansion and Confidence Signal Result

Implemented on 2026-06-05.

Added the next selective P1 statutes:

| Priority | Article | Topic |
|----------|---------|-------|
| P1 | 민법 제35조 | 법인의 불법행위능력 |
| P1 | 민법 제390조 | 채무불이행 손해배상 |

Command result:

```powershell
npm.cmd run collect:laws -- --priority P0,P1
```

```json
{
  "laws_upserted": 2,
  "aliases_upserted": 5,
  "articles_upserted": 14,
  "failed_items": 0
}
```

Post-selective-expansion evaluation:

| Metric | After P1 tort expansion | After selective expansion |
|--------|-------------------------|---------------------------|
| statute precision@10 | 1.000 | 1.000 |
| missing_scope_rate | 0.504 | 0.473 |
| needs_review_rate | 0.770 | 0.770 |
| true_quality_issue_rate | 0.204 | 0.204 |

Confidence penalty was adjusted so syntactically valid but currently missing article refs are no longer treated like extraction failures.

Primary category snapshot:

| Primary category | Count | Rate |
|------------------|-------|------|
| missing_scope | 100 | 0.442 |
| quality_issue | 46 | 0.204 |
| low_confidence | 27 | 0.119 |
| out_of_scope | 1 | 0.004 |
| auto_validated | 52 | 0.230 |

Interpretation:

- The multi-label `low_confidence_rate` is still high because every `needs_review` row is below the current 0.7 threshold.
- The primary signal is different: only `0.119` is primarily a low-confidence-only problem.
- Remaining missing-scope refs are now mostly broad civil-code or mixed-domain provisions: `민법 제103조`, `제162조`, `제2조`, `제163조`, `제398조`, `제477조`, `제741조`, inheritance/property/contract-related provisions.
- Next work should focus on MVP relevance filtering and true quality issue samples rather than continuing broad article expansion.

## 9. MVP Relevance Filtering Result

Implemented on 2026-06-05.

Added `facets.mvp_relevance` to rule-based structures:

```text
mvp_relevant
weakly_related
out_of_scope
```

Search and evaluation now prefer case-level structures with `mvp_relevance` and use the latest relevant structure per case, so older structure rows do not distort search and evaluation metrics.

Pipeline commands:

```powershell
npm.cmd run pipeline:structure -- --limit 300 --overwrite
npm.cmd run pipeline:validate -- --limit 300
npm.cmd run eval:mvp
```

Latest evaluation:

| Metric | Before relevance filtering | After relevance filtering |
|--------|----------------------------|---------------------------|
| natural avg Top-5 relevant count | 2.2 | 2.7 |
| natural avg Top-5 MVP relevant count | n/a | 4.5 |
| compare avg material fact match | 0.697 | 0.772 |
| needs_review_rate | 0.770 | 0.577 |
| true_quality_issue_rate | 0.204 | 0.059 |
| low_confidence_rate | 0.770 | 0.050 |
| primary_low_confidence_rate | 0.119 | 0.000 |

MVP relevance snapshot:

| Relevance | Rate |
|-----------|------|
| mvp_relevant | 0.586 |
| weakly_related | 0.414 |
| out_of_scope | 0.000 |

Interpretation:

- Natural-search Top-5 quality improved materially after relevance-aware ranking.
- The previous high low-confidence signal was largely an artifact of stale structures and mixed validation categories.
- Remaining review work is now mostly `missing_scope` and a smaller true quality issue bucket.
- The next useful task is to inspect `weakly_related` samples and decide whether some should become explicit `out_of_scope`; after that, improve the remaining `quality_issue` samples.

## 10. Weakly Related Tuning Result

Implemented on 2026-06-05.

Inspected recent `weakly_related` samples and found many clear non-MVP titles:

```text
소유권이전등기
임금등
부당이득금
공탁금출급청구권확인
근로자지위확인등
토지인도
임대차보증금
유류분반환
취득세
```

Updated relevance rules so clearly non-MVP case titles are classified as `out_of_scope` even when the body contains incidental damages language.

Latest evaluation after tuning:

| Metric | Before weakly-related tuning | After weakly-related tuning |
|--------|------------------------------|-----------------------------|
| natural avg Top-5 relevant count | 2.7 | 2.8 |
| natural avg Top-5 MVP relevant count | 4.5 | 4.6 |
| compare avg material fact match | 0.772 | 0.807 |
| mvp_relevant_rate | 0.586 | 0.586 |
| weakly_related_rate | 0.414 | 0.118 |
| out_of_scope_relevance_rate | 0.000 | 0.295 |
| needs_review_rate | 0.577 | 0.577 |
| true_quality_issue_rate | 0.059 | 0.059 |

Interpretation:

- The relevance filter now separates a meaningful out-of-scope bucket without hurting natural-search Top-5 quality.
- `weakly_related` is now a smaller review bucket instead of a catch-all for non-MVP cases.
- The next high-value task is to inspect the remaining `quality_issue` rows, now only about 5.9% of latest structures.

## 11. MVP-Focused Data Expansion Result

Implemented on 2026-06-05.

The first 500-case collection attempt reached the API detail phase but failed at final DB upsert because Supabase DNS resolution failed. To reduce retry cost, collection was split into smaller MVP-focused batches:

```powershell
npm.cmd run collect:cases -- --query "교통사고 손해배상" --limit 100 --display 50 --max-pages 2
npm.cmd run collect:cases -- --query "과실상계 손해배상" --limit 100 --display 50 --max-pages 2
npm.cmd run collect:cases -- --query "위자료 손해배상" --limit 100 --display 50 --max-pages 2
```

Each batch succeeded with:

```json
{
  "queries_run": 2,
  "list_rows_seen": 100,
  "unique_case_ids": 100,
  "details_fetched": 100,
  "cases_upserted": 100,
  "failed_items": 0
}
```

Post-collection pipeline:

```powershell
npm.cmd run pipeline:normalize -- --limit 500
npm.cmd run pipeline:split -- --limit 50
npm.cmd run pipeline:structure -- --limit 500 --overwrite
npm.cmd run pipeline:validate -- --limit 500
npm.cmd run pipeline:embed -- --limit 500
npm.cmd run eval:mvp
```

Current DB scale:

| Item | Count |
|------|-------|
| cases | 446 |
| cases with raw text | 445 |
| cases with paragraphs | 445 |
| paragraphs | 61,589 |
| embeddings | 2,456+ |

## 12. Inferred Citation Result

The expanded keyword-based data introduced many rows with strong damages language but no explicit statute citation. Top issue before the fix:

```text
cited_articles_empty: 114
```

Added a conservative inferred citation fallback:

- Only when no explicit citation was extracted.
- Only for strong damages language such as `불법행위`, `손해배상`, `교통사고`, `과실상계`, `위자료`.
- Adds `민법_제750조` with `inferred=true` and an evidence keyword span.
- Applies a smaller confidence boost than explicit citation extraction.

Latest evaluation after expansion and inferred citation:

| Metric | Before expansion | After expansion + inference |
|--------|------------------|-----------------------------|
| cases | 221 | 446 |
| natural avg Top-5 MVP relevant count | 4.6 | 4.8 |
| compare avg material fact match | 0.807 | 0.800 |
| needs_review_rate | 0.577 | 0.429 |
| true_quality_issue_rate | 0.059 | 0.056 |
| missing_scope_rate | 0.491 | 0.362 |
| low_confidence_rate | 0.050 | 0.040 |
| mvp_relevant_rate | 0.586 | 0.724 |
| weakly_related_rate | 0.118 | 0.076 |
| out_of_scope_relevance_rate | 0.295 | 0.200 |

Interpretation:

- The DB is now close to the MVP target range and has a stronger MVP-relevant majority.
- `needs_review_rate` dropped materially even with a larger dataset.
- Remaining review work is mostly missing scope and a small true quality issue bucket.
- The next step should inspect remaining missing-scope refs and decide whether to add only highly relevant statutes such as selected 자동차손해배상 보장법 provisions, rather than widening to broad civil-code general provisions.

## 17. Selected Special-Act Article Expansion Result

Implemented on 2026-06-05.

Latest missing-scope inspection showed repeated 자동차손해배상 보장법 refs among broader civil-code refs:

```text
자동차손해배상 보장법_제5조: 6
자동차손해배상 보장법_제15조: 6
자동차손해배상 보장법_제19조: 4
자동차손해배상 보장법_제12조의2: 4
```

Expanded `docs/StatuteScope.md` with selected P2 traffic-insurance provisions:

| Priority | Article | Topic |
|----------|---------|-------|
| P2 | 자동차손해배상 보장법 제5조 | 보험 등의 가입 의무 |
| P2 | 자동차손해배상 보장법 제12조의2 | 업무의 위탁 |
| P2 | 자동차손해배상 보장법 제15조 | 자동차보험진료수가 등 |
| P2 | 자동차손해배상 보장법 제19조 | 자동차보험진료수가의 심사 청구 등 |

Also added `제조물책임법`/`제조물 책임법` aliases so the existing P2 `제조물 책임법 제3조` row can be collected reliably.

Commands:

```powershell
npm.cmd run collect:laws -- --priority P2 --dry-run
npm.cmd run collect:laws -- --priority P2
npm.cmd run pipeline:validate -- --limit 1000
npm.cmd run eval:mvp
npm.cmd run api:test
```

DB upsert result:

```json
{
  "laws_upserted": 3,
  "aliases_upserted": 7,
  "articles_upserted": 6,
  "failed_items": 0
}
```

Latest evaluation:

| Metric | Before P2 expansion | After P2 expansion |
|--------|---------------------|--------------------|
| needs_review_rate | 0.623 | 0.603 |
| true_quality_issue_rate | 0.247 | 0.235 |
| missing_scope_rate | 0.342 | 0.325 |
| primary_missing_scope_rate | 0.314 | 0.304 |
| natural avg Top-5 domain relevant count | 5 | 5 |
| compare avg domain match score | 0.948 | 0.948 |
| compare avg issue tag overlap | 0.687 | 0.659 |

Validation:

```text
api:test: 52 passed
collect:laws P2 dry-run: failed_items 0
eval:mvp: succeeded
```

Interpretation:

- Selective P2 expansion reduced missing-scope without broad civil-code loading.
- The strongest remaining missing-scope refs are mostly general civil-code, inheritance, unjust-enrichment, and prescription provisions.
- Next useful step is to add a small P1 civil-code general-domain batch from the current missing-scope leaders, then re-run validation and evaluation.

## 18. P1 Civil-Code General Batch Result

Implemented on 2026-06-05.

Added a small P1 civil-code batch from the latest missing-scope leaders:

| Priority | Article | Topic |
|----------|---------|-------|
| P1 | 민법 제2조 | 신의성실, 권리남용 |
| P1 | 민법 제103조 | 반사회질서 법률행위 |
| P1 | 민법 제162조 | 채권 소멸시효 일반 |
| P1 | 민법 제166조 | 소멸시효 기산점 |
| P1 | 민법 제398조 | 손해배상액 예정 |
| P1 | 민법 제741조 | 부당이득 반환 |
| P1 | 민법 제1112조 | 유류분 권리자와 유류분 |
| P1 | 민법 제1114조 | 유류분 산정 재산 |
| P1 | 민법 제1115조 | 유류분 반환 |

Commands:

```powershell
npm.cmd run collect:laws -- --priority P1 --dry-run
npm.cmd run collect:laws -- --priority P1
npm.cmd run pipeline:validate -- --limit 1000
npm.cmd run eval:mvp
npm.cmd run api:test
npm.cmd run web:lint
npm.cmd run web:build
```

DB upsert result:

```json
{
  "laws_upserted": 1,
  "aliases_upserted": 1,
  "articles_upserted": 15,
  "failed_items": 0
}
```

Latest evaluation:

| Metric | Before P1 civil batch | After P1 civil batch |
|--------|-----------------------|----------------------|
| needs_review_rate | 0.603 | 0.595 |
| true_quality_issue_rate | 0.235 | 0.248 |
| missing_scope_rate | 0.325 | 0.291 |
| primary_missing_scope_rate | 0.304 | 0.271 |
| natural avg Top-5 relevant count | 2.438 | 2.438 |
| natural avg Top-5 MVP relevant count | 3.062 | 3.125 |
| natural avg Top-5 domain relevant count | 5 | 5 |
| compare avg material fact match | 0.790 | 0.794 |
| compare avg domain match score | 0.948 | 0.935 |
| compare avg issue tag overlap | 0.659 | 0.692 |

Validation:

```text
api:test: 52 passed
web:lint: passed
web:build: passed
eval:mvp: succeeded
```

Deploy readiness interpretation:

- Internal demo / closed beta: ready if the UI clearly labels results as reference-only and review status remains visible.
- Public MVP: one more quality-focused pass is recommended before release.
- Main blocker is no longer statute search; it is natural-search relevance and the true-quality bucket.
- Practical public-MVP target: `missing_scope_rate <= 0.25`, `true_quality_issue_rate <= 0.20`, natural avg Top-5 relevant count `>= 3.0`, and all build/test checks passing.

## 19. Quality Classification and Natural Intent Boost Result

Implemented on 2026-06-05.

Two small release-readiness fixes were applied:

1. Validation primary-category selection now prioritizes explicit `facets.mvp_relevance = out_of_scope`.
   - Existing reason/category lists are preserved.
   - This separates true parser failures from cases that are simply outside the MVP/search scope.

2. Natural-search intent parsing now expands common legal paraphrases.
   - `잘못`, `감액`, `줄어든` -> `과실`, `과실상계`, `배상액`
   - `회사 직원`, `업무 중`, `사용자 책임` -> `사용자책임`
   - `여러 사람`, `함께`, `공동` -> `공동불법행위`
   - `통상손해`, `특별손해`, `배상 범위` -> 손해배상 범위 terms
   - Inferred articles now use internal normalized refs such as `민법_제396조` instead of old placeholder ids.

Latest evaluation:

| Metric | Before | After |
|--------|--------|-------|
| natural avg Top-5 relevant count | 2.500 | 3.750 |
| natural avg Top-5 MVP relevant count | 3.125 | 3.125 |
| natural avg Top-5 domain relevant count | 5 | 5 |
| needs_review_rate | 0.592 | 0.592 |
| primary_quality_issue_rate | 0.248 before primary fix / 0.113 after | 0.113 |
| primary_missing_scope_rate | 0.271 before primary fix | 0.206 |
| primary_out_of_scope_rate | 0.075 before primary fix | 0.273 |
| compare avg material fact match | 0.790 | 0.722 |
| compare avg domain match score | 0.948 | 0.948 |
| compare avg issue tag overlap | 0.674 | 0.478 |

Validation:

```text
api:test: 53 passed
web:lint: passed
web:build: passed
eval:mvp: succeeded
```

Release-readiness interpretation:

- Public MVP / class demo deployment is now acceptable if the product copy clearly says results are reference material and not legal advice.
- The remaining caution is compare-candidate issue-tag overlap, which fell after the natural-search base set changed.
- Next improvement should tune compare candidate ranking or issue-tag extraction, not statute search.

## 20. Compare Ranking Release Tuning Result

Implemented on 2026-06-05.

Adjusted compare-candidate ranking for feedback-ready MVP behavior:

- Increased weight for `issue_tag_overlap`.
- Increased weight for `material_fact_match`.
- Reduced reliance on same-domain matching alone.
- Added penalties when the base case has issue tags but the candidate has none, or when material-fact match is very low.

Latest evaluation:

| Metric | Before compare tuning | After compare tuning |
|--------|-----------------------|----------------------|
| natural avg Top-5 relevant count | 3.750 | 3.750 |
| compare avg material fact match | 0.722 | 0.716 |
| compare avg domain match score | 0.948 | 0.948 |
| compare avg issue tag overlap | 0.478 | 0.528 |
| evidence coverage rate | 1.0 | 1.0 |

Validation:

```text
api:test: 53 passed
web:lint: passed
web:build: passed
eval:mvp: succeeded
```

Interpretation:

- The compare candidate list is now less likely to rank same-domain but issue-unrelated cases first.
- Material-fact score moved slightly down, but issue alignment improved, which is better for first user feedback quality.
- This is good enough for an MVP launch where users will provide feedback, as long as feedback labels are monitored.

## 21. Feedback-MVP Data Expansion Result

Implemented on 2026-06-05.

Expanded the precedent DB from 613 cases to 1,076 cases for feedback-ready MVP coverage.

Collection batches:

```powershell
npm.cmd run collect:cases -- --scope general --query "계약대금 채무불이행 손해배상" --limit 100 --display 50 --max-pages 2
npm.cmd run collect:cases -- --scope general --query "상속재산 분할 유류분 반환" --limit 100 --display 50 --max-pages 2
npm.cmd run collect:cases -- --scope general --query "보험금 구상금 보험자대위 손해배상" --limit 100 --display 50 --max-pages 2
npm.cmd run collect:cases -- --scope general --query "이혼 위자료 재산분할 손해배상" --limit 100 --display 50 --max-pages 2
npm.cmd run collect:cases -- --scope general --query "소유권이전등기 말소등기 부동산" --limit 100 --display 50 --max-pages 2
npm.cmd run collect:cases -- --scope general --query "임대차보증금 반환 건물명도" --limit 100 --display 50 --max-pages 2
npm.cmd run collect:cases -- --scope general --query "부당이득 반환청구 법률상 원인" --limit 100 --display 50 --max-pages 2
npm.cmd run collect:cases -- --scope general --query "근로자 임금 퇴직금 해고" --limit 100 --display 50 --max-pages 2
npm.cmd run collect:cases -- --scope general --query "취득세 부과처분 취소 경정청구" --limit 100 --display 50 --max-pages 2
npm.cmd run collect:cases -- --scope general --query "보험금 청구 보험자대위 구상금" --limit 100 --display 50 --max-pages 2
```

Processing pipeline:

```powershell
npm.cmd run pipeline:normalize -- --limit 1600
npm.cmd run pipeline:split -- --limit 100
npm.cmd run pipeline:split -- --limit 100
npm.cmd run pipeline:split -- --limit 100
npm.cmd run pipeline:structure -- --limit 1600 --overwrite
npm.cmd run pipeline:validate -- --limit 2200
npm.cmd run pipeline:embed -- --limit 2200
npm.cmd run eval:mvp
npm.cmd run api:test
npm.cmd run web:lint
npm.cmd run web:build
```

Latest DB scale:

| Item | Count |
|------|------:|
| cases | 1,076 |
| paragraphs | 119,542 |
| structures | 1,943 |
| embeddings | 9,267 |

Latest primary domain distribution:

| Domain | Count |
|--------|------:|
| damages | 532 |
| labor | 114 |
| unjust_enrichment | 94 |
| lease | 86 |
| tax | 81 |
| property | 53 |
| inheritance | 49 |
| family | 26 |
| contract | 24 |
| insurance | 9 |
| ip | 5 |
| general | 2 |

Latest evaluation:

| Metric | Value |
|--------|------:|
| statute precision@10 | 1.0 |
| natural avg Top-5 relevant count | 3.625 |
| natural avg Top-5 MVP relevant count | 3.312 |
| natural avg Top-5 domain relevant count | 5 |
| compare avg material fact match | 0.836 |
| compare avg domain match score | 1.0 |
| compare avg issue tag overlap | 0.778 |
| evidence coverage rate | 1.0 |
| needs_review_rate | 0.607 |
| true_quality_issue_rate | 0.126 |
| primary_quality_issue_rate | 0.061 |
| primary_missing_scope_rate | 0.180 |

Validation:

```text
api:test: 53 passed
web:lint: passed
web:build: passed
eval:mvp: succeeded
```

Interpretation:

- The DB is now inside the 1,000-1,200 case feedback-MVP target range.
- Compare quality improved after the larger domain-balanced corpus.
- Labor, unjust enrichment, lease, and tax are now usable for feedback collection.
- Contract, insurance, family, and inheritance are still thinner than ideal, but no longer block MVP feedback launch.
