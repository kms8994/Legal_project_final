-- HNSW 인덱스: IVFFlat 대비 정확도 높고 업데이트에 강함
-- pgvector 0.5.0+ 필요 (Supabase 기본 포함)
drop index if exists idx_case_embeddings_vector;

create index if not exists idx_case_embeddings_hnsw
  on case_embeddings using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);

-- case_summaries: case_id 조회 성능 (unique constraint가 이미 인덱스 생성하지만 명시)
create index if not exists idx_case_summaries_case_id
  on case_summaries (case_id);

-- case_summaries: 생성일 기준 최신 확인용
create index if not exists idx_case_summaries_updated_at
  on case_summaries (updated_at desc);

-- cases: is_deleted + decision_date 복합 (검색 where 절 최적화)
create index if not exists idx_cases_active_date
  on cases (is_deleted, decision_date desc nulls last)
  where is_deleted = false;

-- case_structures: case_id + processed_at (distinct on 최적화)
create index if not exists idx_case_structures_case_processed
  on case_structures (case_id, processed_at desc);

-- case_embeddings: type + model 필터 (벡터 검색 where 조건)
create index if not exists idx_case_embeddings_type_model
  on case_embeddings (embedding_type, embedding_model, needs_regeneration)
  where needs_regeneration = false;
