create table if not exists pipeline_runs (
  id uuid primary key default gen_random_uuid(),
  stage text not null,
  status text not null,
  source text,
  params jsonb not null default '{}'::jsonb,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  input_count integer not null default 0,
  success_count integer not null default 0,
  failed_count integer not null default 0,
  error_summary text
);

create table if not exists laws (
  id uuid primary key default gen_random_uuid(),
  law_code text not null,
  official_name text not null,
  short_name text,
  effective_date date,
  source_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (law_code, effective_date)
);

create table if not exists law_aliases (
  id uuid primary key default gen_random_uuid(),
  law_id uuid not null references laws(id) on delete cascade,
  alias text not null,
  created_at timestamptz not null default now(),
  unique (law_id, alias)
);

create table if not exists articles (
  id uuid primary key default gen_random_uuid(),
  law_id uuid not null references laws(id) on delete cascade,
  article_code text,
  article_no integer not null,
  article_branch_no integer,
  paragraph_no integer,
  subparagraph_no integer,
  title text,
  body text not null default '',
  normalized_ref text not null,
  effective_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists idx_articles_unique_ref
  on articles (
    law_id,
    article_no,
    coalesce(article_branch_no, 0),
    coalesce(paragraph_no, 0),
    coalesce(subparagraph_no, 0),
    coalesce(effective_date, date '1900-01-01')
  );

create table if not exists cases (
  id uuid primary key default gen_random_uuid(),
  external_id text not null,
  case_no text not null,
  court_name text not null,
  court_level text,
  decision_date date,
  case_name text not null,
  case_type text,
  legal_domain text,
  source text not null default 'law.go.kr',
  source_url text,
  raw_text text not null default '',
  raw_html text,
  source_hash text not null,
  pipeline_run_id uuid references pipeline_runs(id) on delete set null,
  is_deleted boolean not null default false,
  collected_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (external_id),
  unique (case_no, decision_date, court_name),
  unique (source_hash)
);

create table if not exists case_paragraphs (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references cases(id) on delete cascade,
  paragraph_id text not null,
  section_type text not null default 'unknown',
  paragraph_order integer not null,
  text text not null,
  char_start integer,
  char_end integer,
  content_hash text not null,
  created_at timestamptz not null default now(),
  unique (case_id, paragraph_id),
  unique (case_id, paragraph_order)
);

create table if not exists prompt_versions (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  version text not null,
  purpose text not null,
  content_hash text not null,
  created_at timestamptz not null default now(),
  notes text,
  unique (name, version)
);

create table if not exists case_structures (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references cases(id) on delete cascade,
  cited_articles jsonb not null default '[]'::jsonb,
  referenced_cases jsonb not null default '[]'::jsonb,
  facts text,
  facts_timeline jsonb not null default '[]'::jsonb,
  actors jsonb not null default '[]'::jsonb,
  actions jsonb not null default '[]'::jsonb,
  harm jsonb not null default '{}'::jsonb,
  causation jsonb not null default '{}'::jsonb,
  legal_issue text,
  court_reasoning text,
  conclusion text,
  material_facts jsonb not null default '{}'::jsonb,
  aggravating_factors jsonb not null default '[]'::jsonb,
  mitigating_factors jsonb not null default '[]'::jsonb,
  key_disputed_facts jsonb not null default '[]'::jsonb,
  outcome jsonb not null default '{}'::jsonb,
  facets jsonb not null default '{}'::jsonb,
  evidence_spans jsonb not null default '{}'::jsonb,
  confidence_score numeric(4, 3) not null default 0,
  review_status text not null default 'pending',
  is_reviewed boolean not null default false,
  prompt_version text,
  model_name text,
  structure_hash text not null,
  processed_at timestamptz not null default now(),
  unique (case_id, structure_hash)
);

create table if not exists case_embeddings (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references cases(id) on delete cascade,
  paragraph_id uuid references case_paragraphs(id) on delete cascade,
  embedding_type text not null,
  embedding_model text not null,
  embedding_dimension integer not null,
  content_text text not null,
  content_hash text not null,
  embedding vector(768) not null,
  needs_regeneration boolean not null default false,
  created_at timestamptz not null default now(),
  unique (case_id, paragraph_id, embedding_type, embedding_model, content_hash)
);

create table if not exists search_queries (
  id uuid primary key default gen_random_uuid(),
  user_id text,
  query_text text not null,
  query_type text not null,
  parsed_query jsonb not null default '{}'::jsonb,
  result_count integer not null default 0,
  latency_ms integer,
  created_at timestamptz not null default now()
);

create table if not exists comparison_feedbacks (
  id uuid primary key default gen_random_uuid(),
  user_id text,
  query_id uuid references search_queries(id) on delete set null,
  base_case_id uuid references cases(id) on delete set null,
  compare_case_id uuid references cases(id) on delete set null,
  label text not null,
  reason text,
  comment text,
  created_at timestamptz not null default now()
);

create table if not exists llm_runs (
  id uuid primary key default gen_random_uuid(),
  purpose text not null,
  model_name text not null,
  prompt_version text,
  input_hash text not null,
  output jsonb,
  latency_ms integer,
  token_input integer,
  token_output integer,
  cost_usd numeric(12, 6),
  status text not null,
  error_message text,
  created_at timestamptz not null default now()
);

create index if not exists idx_cases_case_no on cases(case_no);
create index if not exists idx_cases_decision_date on cases(decision_date desc);
create index if not exists idx_cases_court_level on cases(court_level);
create index if not exists idx_cases_legal_domain on cases(legal_domain);
create index if not exists idx_case_paragraphs_case_order on case_paragraphs(case_id, paragraph_order);
create index if not exists idx_articles_normalized_ref on articles(normalized_ref);
create index if not exists idx_search_queries_created_at on search_queries(created_at desc);

create index if not exists idx_case_structures_cited_articles on case_structures using gin(cited_articles);
create index if not exists idx_case_structures_outcome on case_structures using gin(outcome);
create index if not exists idx_case_structures_facets on case_structures using gin(facets);
create index if not exists idx_case_structures_material_facts on case_structures using gin(material_facts);

create index if not exists idx_case_embeddings_vector
  on case_embeddings using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);
