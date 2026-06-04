begin;

insert into pipeline_runs (
  stage,
  status,
  source,
  params,
  finished_at,
  input_count,
  success_count,
  failed_count
)
select
  'seed_sample_cases',
  'succeeded',
  'manual_seed',
  '{"seed_file": "db/seeds/001_sample_cases.sql", "purpose": "Supabase smoke test"}'::jsonb,
  now(),
  3,
  3,
  0
where not exists (
  select 1
  from pipeline_runs
  where stage = 'seed_sample_cases'
    and source = 'manual_seed'
    and params->>'seed_file' = 'db/seeds/001_sample_cases.sql'
);

with law_seed(law_code, official_name, short_name, effective_date, source_url) as (
  values
    ('001761', '민법', '민법', date '2026-01-01', 'https://www.law.go.kr/법령/민법')
)
insert into laws (
  law_code,
  official_name,
  short_name,
  effective_date,
  source_url
)
select
  law_code,
  official_name,
  short_name,
  effective_date,
  source_url
from law_seed
on conflict (law_code, effective_date) do update set
  official_name = excluded.official_name,
  short_name = excluded.short_name,
  source_url = excluded.source_url,
  updated_at = now();

with alias_seed(official_name, effective_date, alias) as (
  values
    ('민법', date '2026-01-01', '민법'),
    ('민법', date '2026-01-01', '민 법')
)
insert into law_aliases (
  law_id,
  alias
)
select
  laws.id,
  alias_seed.alias
from alias_seed
join laws
  on laws.official_name = alias_seed.official_name
 and laws.effective_date = alias_seed.effective_date
on conflict (law_id, alias) do nothing;

with article_seed(
  official_name,
  effective_date,
  article_code,
  article_no,
  article_branch_no,
  paragraph_no,
  subparagraph_no,
  title,
  body,
  normalized_ref
) as (
  values
    (
      '민법',
      date '2026-01-01',
      '750',
      750,
      null::integer,
      null::integer,
      null::integer,
      '불법행위의 내용',
      '고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자는 그 손해를 배상할 책임이 있다.',
      '민법_제750조'
    ),
    (
      '민법',
      date '2026-01-01',
      '751',
      751,
      null::integer,
      null::integer,
      null::integer,
      '재산 이외의 손해의 배상',
      '타인의 신체, 자유 또는 명예를 해하거나 기타 정신상 고통을 가한 자는 재산 이외의 손해에 대하여도 배상할 책임이 있다.',
      '민법_제751조'
    ),
    (
      '민법',
      date '2026-01-01',
      '396',
      396,
      null::integer,
      null::integer,
      null::integer,
      '과실상계',
      '채무불이행에 관하여 채권자에게 과실이 있는 때에는 법원은 손해배상의 책임 및 그 금액을 정함에 이를 참작하여야 한다.',
      '민법_제396조'
    )
)
insert into articles (
  law_id,
  article_code,
  article_no,
  article_branch_no,
  paragraph_no,
  subparagraph_no,
  title,
  body,
  normalized_ref,
  effective_date
)
select
  laws.id,
  article_seed.article_code,
  article_seed.article_no,
  article_seed.article_branch_no,
  article_seed.paragraph_no,
  article_seed.subparagraph_no,
  article_seed.title,
  article_seed.body,
  article_seed.normalized_ref,
  article_seed.effective_date
from article_seed
join laws
  on laws.official_name = article_seed.official_name
 and laws.effective_date = article_seed.effective_date
on conflict (
  law_id,
  article_no,
  (coalesce(article_branch_no, 0)),
  (coalesce(paragraph_no, 0)),
  (coalesce(subparagraph_no, 0)),
  (coalesce(effective_date, date '1900-01-01'))
) do update set
  article_code = excluded.article_code,
  title = excluded.title,
  body = excluded.body,
  normalized_ref = excluded.normalized_ref,
  updated_at = now();

with latest_seed_run as (
  select id
  from pipeline_runs
  where stage = 'seed_sample_cases'
  order by started_at desc
  limit 1
),
case_seed(
  external_id,
  case_no,
  court_name,
  court_level,
  decision_date,
  case_name,
  case_type,
  legal_domain,
  source_url,
  raw_text,
  raw_html,
  source_hash
) as (
  values
    (
      'SAMPLE-CASE-001',
      '2024가단100001',
      '서울중앙지방법원',
      '지방법원',
      date '2024-05-10',
      '손해배상(교통사고)',
      '민사',
      '손해배상',
      'https://www.law.go.kr/판례/SAMPLE-CASE-001',
      '원고는 횡단보도 부근에서 피고 차량과 충돌하여 상해를 입었다. 피고 운전자는 전방주시의무를 게을리하였고 제한속도를 초과하였다. 다만 원고도 신호 변경 직전 급히 진입한 과실이 있다. 법원은 피고의 불법행위책임을 인정하되 원고 과실 30퍼센트를 참작하였다.',
      '<p>원고는 횡단보도 부근에서 피고 차량과 충돌하여 상해를 입었다.</p><p>피고 운전자는 전방주시의무를 게을리하였다.</p>',
      'seed-sample-case-001'
    ),
    (
      'SAMPLE-CASE-002',
      '2023나100002',
      '서울고등법원',
      '고등법원',
      date '2023-11-22',
      '손해배상(명예훼손)',
      '민사',
      '손해배상',
      'https://www.law.go.kr/판례/SAMPLE-CASE-002',
      '피고는 온라인 게시글을 통하여 원고의 명예를 훼손하는 표현을 반복적으로 게시하였다. 원고는 정신적 고통에 대한 위자료를 청구하였다. 법원은 표현의 위법성과 고의성을 인정하고 위자료 일부를 인용하였다.',
      '<p>피고는 온라인 게시글을 통하여 원고의 명예를 훼손하는 표현을 반복적으로 게시하였다.</p>',
      'seed-sample-case-002'
    ),
    (
      'SAMPLE-CASE-003',
      '2022가단100003',
      '수원지방법원',
      '지방법원',
      date '2022-08-19',
      '손해배상(공사현장 사고)',
      '민사',
      '손해배상',
      'https://www.law.go.kr/판례/SAMPLE-CASE-003',
      '원고는 공사 현장 인접 보행로에서 낙하물로 상해를 입었다. 시공사와 하도급업체는 안전망 설치 및 통행 제한 조치를 충분히 하지 않았다. 법원은 주의의무 위반과 손해 사이의 상당인과관계를 인정하였다.',
      '<p>원고는 공사 현장 인접 보행로에서 낙하물로 상해를 입었다.</p>',
      'seed-sample-case-003'
    )
)
insert into cases (
  external_id,
  case_no,
  court_name,
  court_level,
  decision_date,
  case_name,
  case_type,
  legal_domain,
  source_url,
  raw_text,
  raw_html,
  source_hash,
  pipeline_run_id
)
select
  case_seed.external_id,
  case_seed.case_no,
  case_seed.court_name,
  case_seed.court_level,
  case_seed.decision_date,
  case_seed.case_name,
  case_seed.case_type,
  case_seed.legal_domain,
  case_seed.source_url,
  case_seed.raw_text,
  case_seed.raw_html,
  case_seed.source_hash,
  latest_seed_run.id
from case_seed
cross join latest_seed_run
on conflict (external_id) do update set
  case_no = excluded.case_no,
  court_name = excluded.court_name,
  court_level = excluded.court_level,
  decision_date = excluded.decision_date,
  case_name = excluded.case_name,
  case_type = excluded.case_type,
  legal_domain = excluded.legal_domain,
  source_url = excluded.source_url,
  raw_text = excluded.raw_text,
  raw_html = excluded.raw_html,
  source_hash = excluded.source_hash,
  pipeline_run_id = excluded.pipeline_run_id,
  updated_at = now();

with paragraph_seed(external_id, paragraph_id, section_type, paragraph_order, text, char_start, char_end, content_hash) as (
  values
    ('SAMPLE-CASE-001', 'P001', 'facts', 1, '원고는 횡단보도 부근에서 피고 차량과 충돌하여 상해를 입었다.', 0, 34, 'seed-sample-case-001-p001'),
    ('SAMPLE-CASE-001', 'P002', 'reasoning', 2, '피고 운전자는 전방주시의무를 게을리하였고 제한속도를 초과하였다.', 35, 72, 'seed-sample-case-001-p002'),
    ('SAMPLE-CASE-001', 'P003', 'reasoning', 3, '다만 원고도 신호 변경 직전 급히 진입한 과실이 있다.', 73, 105, 'seed-sample-case-001-p003'),
    ('SAMPLE-CASE-001', 'P004', 'order', 4, '법원은 피고의 불법행위책임을 인정하되 원고 과실 30퍼센트를 참작하였다.', 106, 145, 'seed-sample-case-001-p004'),
    ('SAMPLE-CASE-002', 'P001', 'facts', 1, '피고는 온라인 게시글을 통하여 원고의 명예를 훼손하는 표현을 반복적으로 게시하였다.', 0, 45, 'seed-sample-case-002-p001'),
    ('SAMPLE-CASE-002', 'P002', 'claim', 2, '원고는 정신적 고통에 대한 위자료를 청구하였다.', 46, 72, 'seed-sample-case-002-p002'),
    ('SAMPLE-CASE-002', 'P003', 'reasoning', 3, '법원은 표현의 위법성과 고의성을 인정하였다.', 73, 97, 'seed-sample-case-002-p003'),
    ('SAMPLE-CASE-002', 'P004', 'order', 4, '위자료 일부를 인용하였다.', 98, 112, 'seed-sample-case-002-p004'),
    ('SAMPLE-CASE-003', 'P001', 'facts', 1, '원고는 공사 현장 인접 보행로에서 낙하물로 상해를 입었다.', 0, 34, 'seed-sample-case-003-p001'),
    ('SAMPLE-CASE-003', 'P002', 'reasoning', 2, '시공사와 하도급업체는 안전망 설치 및 통행 제한 조치를 충분히 하지 않았다.', 35, 76, 'seed-sample-case-003-p002'),
    ('SAMPLE-CASE-003', 'P003', 'reasoning', 3, '법원은 주의의무 위반과 손해 사이의 상당인과관계를 인정하였다.', 77, 112, 'seed-sample-case-003-p003')
)
insert into case_paragraphs (
  case_id,
  paragraph_id,
  section_type,
  paragraph_order,
  text,
  char_start,
  char_end,
  content_hash
)
select
  cases.id,
  paragraph_seed.paragraph_id,
  paragraph_seed.section_type,
  paragraph_seed.paragraph_order,
  paragraph_seed.text,
  paragraph_seed.char_start,
  paragraph_seed.char_end,
  paragraph_seed.content_hash
from paragraph_seed
join cases
  on cases.external_id = paragraph_seed.external_id
on conflict (case_id, paragraph_id) do update set
  section_type = excluded.section_type,
  paragraph_order = excluded.paragraph_order,
  text = excluded.text,
  char_start = excluded.char_start,
  char_end = excluded.char_end,
  content_hash = excluded.content_hash;

with structure_seed(
  external_id,
  cited_articles,
  facts,
  actors,
  actions,
  harm,
  causation,
  legal_issue,
  court_reasoning,
  conclusion,
  material_facts,
  aggravating_factors,
  mitigating_factors,
  key_disputed_facts,
  outcome,
  facets,
  evidence_spans,
  confidence_score,
  review_status,
  prompt_version,
  model_name,
  structure_hash
) as (
  values
    (
      'SAMPLE-CASE-001',
      '[{"normalized_ref": "민법_제750조"}, {"normalized_ref": "민법_제396조"}]'::jsonb,
      '횡단보도 부근 교통사고에서 운전자 과실과 보행자 과실이 함께 문제된 사안',
      '["보행자", "차량 운전자"]'::jsonb,
      '["전방주시의무 위반", "신호 변경 직전 진입"]'::jsonb,
      '{"injury_type": "신체 상해", "damage_scope_issue": "치료비와 위자료"}'::jsonb,
      '{"causation_dispute": false, "recognized": true}'::jsonb,
      '불법행위책임 성립과 과실상계 비율',
      '피고의 전방주시의무 위반을 인정하되 원고의 진입 경위도 손해배상액 산정에 참작하였다.',
      '피고 책임을 인정하고 원고 과실 30퍼센트를 반영하였다.',
      '{"accident_type": "교통사고", "victim_status": "보행자", "defendant_conduct": "전방주시의무 위반", "negligence_offset_issue": true}'::jsonb,
      '["제한속도 초과"]'::jsonb,
      '["원고 과실 존재"]'::jsonb,
      '["과실상계 비율"]'::jsonb,
      '{"disposition": "일부 인용", "direction": "원고 일부 승소", "relief_type": "손해배상", "ratio_or_percentage": "원고 과실 30퍼센트", "key_factor": "과실상계"}'::jsonb,
      '{"legal_domain": "손해배상", "case_type": "민사", "harm_type": "신체", "court_level": "지방법원"}'::jsonb,
      '{"facts": ["P001"], "reasoning": ["P002", "P003"], "outcome": ["P004"]}'::jsonb,
      0.820,
      'pending',
      'seed-v1',
      'manual-seed',
      'seed-sample-case-001-structure'
    ),
    (
      'SAMPLE-CASE-002',
      '[{"normalized_ref": "민법_제750조"}, {"normalized_ref": "민법_제751조"}]'::jsonb,
      '온라인 게시글로 인한 명예훼손과 정신적 손해가 문제된 사안',
      '["게시글 작성자", "피해자"]'::jsonb,
      '["명예훼손 표현 반복 게시"]'::jsonb,
      '{"injury_type": "정신적 손해", "damage_scope_issue": "위자료"}'::jsonb,
      '{"causation_dispute": false, "recognized": true}'::jsonb,
      '위법한 표현으로 인한 위자료 인정 여부',
      '반복 게시된 표현의 위법성과 고의성을 인정하였다.',
      '위자료 일부를 인용하였다.',
      '{"accident_type": "명예훼손", "defendant_conduct": "반복 게시", "injury_type": "정신적 고통", "negligence_offset_issue": false}'::jsonb,
      '["반복 게시"]'::jsonb,
      '[]'::jsonb,
      '["표현의 위법성", "손해 범위"]'::jsonb,
      '{"disposition": "일부 인용", "direction": "원고 일부 승소", "relief_type": "위자료", "key_factor": "위법 표현과 정신적 손해"}'::jsonb,
      '{"legal_domain": "손해배상", "case_type": "민사", "harm_type": "정신", "court_level": "고등법원"}'::jsonb,
      '{"facts": ["P001"], "claim": ["P002"], "reasoning": ["P003"], "outcome": ["P004"]}'::jsonb,
      0.790,
      'pending',
      'seed-v1',
      'manual-seed',
      'seed-sample-case-002-structure'
    ),
    (
      'SAMPLE-CASE-003',
      '[{"normalized_ref": "민법_제750조"}]'::jsonb,
      '공사 현장 인접 보행로 낙하물 사고에서 안전조치 위반이 문제된 사안',
      '["보행자", "시공사", "하도급업체"]'::jsonb,
      '["안전망 미설치", "통행 제한 조치 미흡"]'::jsonb,
      '{"injury_type": "신체 상해", "damage_scope_issue": "치료비와 일실수입"}'::jsonb,
      '{"causation_dispute": true, "recognized": true}'::jsonb,
      '안전조치 위반과 손해 사이의 상당인과관계',
      '안전망 설치와 통행 제한 조치가 부족했고 그 위반과 손해 사이의 인과관계를 인정하였다.',
      '치료비와 일실수입 일부를 인정하였다.',
      '{"accident_type": "공사현장 사고", "victim_status": "보행자", "defendant_conduct": "안전조치 미흡", "causation_dispute": true}'::jsonb,
      '["안전망 미설치"]'::jsonb,
      '["장래 손해 일부 증거 부족"]'::jsonb,
      '["상당인과관계", "손해 범위"]'::jsonb,
      '{"disposition": "일부 인용", "direction": "원고 일부 승소", "relief_type": "손해배상", "key_factor": "안전조치 위반과 인과관계"}'::jsonb,
      '{"legal_domain": "손해배상", "case_type": "민사", "harm_type": "신체", "court_level": "지방법원"}'::jsonb,
      '{"facts": ["P001"], "reasoning": ["P002", "P003"]}'::jsonb,
      0.810,
      'pending',
      'seed-v1',
      'manual-seed',
      'seed-sample-case-003-structure'
    )
)
insert into case_structures (
  case_id,
  cited_articles,
  facts,
  actors,
  actions,
  harm,
  causation,
  legal_issue,
  court_reasoning,
  conclusion,
  material_facts,
  aggravating_factors,
  mitigating_factors,
  key_disputed_facts,
  outcome,
  facets,
  evidence_spans,
  confidence_score,
  review_status,
  prompt_version,
  model_name,
  structure_hash
)
select
  cases.id,
  structure_seed.cited_articles,
  structure_seed.facts,
  structure_seed.actors,
  structure_seed.actions,
  structure_seed.harm,
  structure_seed.causation,
  structure_seed.legal_issue,
  structure_seed.court_reasoning,
  structure_seed.conclusion,
  structure_seed.material_facts,
  structure_seed.aggravating_factors,
  structure_seed.mitigating_factors,
  structure_seed.key_disputed_facts,
  structure_seed.outcome,
  structure_seed.facets,
  structure_seed.evidence_spans,
  structure_seed.confidence_score,
  structure_seed.review_status,
  structure_seed.prompt_version,
  structure_seed.model_name,
  structure_seed.structure_hash
from structure_seed
join cases
  on cases.external_id = structure_seed.external_id
on conflict (case_id, structure_hash) do update set
  cited_articles = excluded.cited_articles,
  facts = excluded.facts,
  actors = excluded.actors,
  actions = excluded.actions,
  harm = excluded.harm,
  causation = excluded.causation,
  legal_issue = excluded.legal_issue,
  court_reasoning = excluded.court_reasoning,
  conclusion = excluded.conclusion,
  material_facts = excluded.material_facts,
  aggravating_factors = excluded.aggravating_factors,
  mitigating_factors = excluded.mitigating_factors,
  key_disputed_facts = excluded.key_disputed_facts,
  outcome = excluded.outcome,
  facets = excluded.facets,
  evidence_spans = excluded.evidence_spans,
  confidence_score = excluded.confidence_score,
  review_status = excluded.review_status,
  prompt_version = excluded.prompt_version,
  model_name = excluded.model_name,
  processed_at = now();

commit;
