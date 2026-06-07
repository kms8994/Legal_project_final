-- 005: case_structures 중복 제거 + validate 후 is_reviewed 표시
-- 각 case_id에서 processed_at 최신 레코드 하나만 남기고 나머지 삭제

delete from case_structures
where id not in (
  select distinct on (case_id) id
  from case_structures
  order by case_id, processed_at desc
);

-- validate 파이프라인이 is_reviewed=true 를 세팅하도록
-- 현재 auto_validated인 레코드는 이미 검증 완료 표시
update case_structures
set is_reviewed = true
where review_status = 'auto_validated';
