-- case_summaries: 표시 전용 사전 생성 요약
-- 검색/매칭 로직에 사용하지 않음. 화면 렌더링에만 사용.
create table if not exists case_summaries (
  id             uuid primary key default gen_random_uuid(),
  case_id        uuid not null references cases(id) on delete cascade,
  one_line       text not null,        -- 검색 카드 한 줄 요약 (40자 이내 목표)
  facts_summary  text not null,        -- 사실관계 2-3문장
  issue_summary  text,                 -- 법적 쟁점 1-2문장
  reasoning_summary text,             -- 법원의 판단 근거 2-3문장
  judgment_summary  text not null,    -- 판결 결과 자연어 1-2문장
  disposition    text,                 -- 정제된 disposition enum: 기각/인용/파기환송/일부인용/기타
  generated_by   text not null,        -- 생성 모델명 (gemini-2.5-flash 등)
  input_hash     text not null,        -- 같은 입력이면 재생성 건너뜀
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (case_id)
);

create index if not exists idx_case_summaries_case_id on case_summaries(case_id);
