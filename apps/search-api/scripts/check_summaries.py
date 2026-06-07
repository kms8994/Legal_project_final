from app.db.session import engine
from sqlalchemy import text
import sys

with engine.connect() as conn:
    cnt = conn.execute(text("select count(*) from case_summaries")).scalar()
    total = conn.execute(text("select count(*) from cases where is_deleted=false")).scalar()
    sys.stdout.buffer.write(f"summaries: {cnt}/{total}\n".encode("utf-8"))

    # 최신 판례 10개와 summary 여부
    rows = conn.execute(text("""
        select c.case_no, c.decision_date::text,
               (cs.id is not null) as has_sum,
               cs.one_line
        from cases c
        left join case_summaries cs on cs.case_id = c.id
        where c.is_deleted = false
        order by c.decision_date desc nulls last
        limit 10
    """)).mappings().all()
    for r in rows:
        line = f"{r['case_no']} ({r['decision_date']}) has_sum={r['has_sum']} | {r['one_line'] or ''}\n"
        sys.stdout.buffer.write(line.encode("utf-8"))
