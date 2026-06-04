# Data Collection Runbook

## 1. 목적

이 문서는 CaseLens MVP의 첫 데이터 수집 검증 절차다. 법령정보센터 Open API를 런타임 백엔드에서 직접 호출하지 않고, 로컬/배치 파이프라인에서만 호출해 PostgreSQL에 적재한다.

현재 단계의 목표는 API 키만 넣으면 아래 항목을 샘플 호출로 검증할 수 있게 만드는 것이다.

- 법령 목록 조회
- 법령 본문 조회
- 판례 목록 조회
- 판례 상세 조회
- P0 조문별 판례 검색 가능성 확인
- 응답 필드와 내부 DB 필드 매핑 초안 확인

## 2. 준비물

법령정보센터 Open API 인증값인 `OC`가 필요하다.

```powershell
Copy-Item .env.example .env
```

이미 `.env` 파일은 만들어져 있으므로, 실제로는 아래 값만 채우면 된다.

```dotenv
LAW_API_OC=발급받은_OC_값
```

참고한 공식 가이드:

- 법령 목록 조회: `lawSearch.do?target=law` 또는 `target=eflaw`
- 법령 본문 조회: `lawService.do?target=eflaw`
- 판례 목록 조회: `lawSearch.do?target=prec`
- 판례 본문 조회: `lawService.do?target=prec`

## 3. 샘플 호출 실행

```powershell
python scripts\law_api_probe.py
```

현재 PC처럼 `python` 명령이 PATH에 없을 수 있으므로, Windows에서는 아래 래퍼를 우선 사용한다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_law_api_probe.ps1
```

선택 옵션:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_law_api_probe.ps1 -CaseQuery "교통사고 손해배상" -Display 10
```

성공하면 `data/api_samples/` 아래에 다음 파일이 생긴다.

```text
01_law_search_minbeop.json
02_law_detail_minbeop.json
03_case_search_damages.json
04_case_detail_first_result.json
05_p0_case_search_01.json
05_p0_case_search_02.json
...
```

`.env`와 API 응답 샘플은 `.gitignore`에 포함되어 커밋되지 않는다.

## 4. 검증 대상 P0 조문

| 우선순위 | 조문 | 목적 |
|----------|------|------|
| P0 | 민법 제750조 | 불법행위 손해배상 일반 |
| P0 | 민법 제751조 | 재산 이외 손해, 위자료 |
| P0 | 민법 제763조 | 불법행위 손해배상 준용 |
| P0 | 민법 제393조 | 손해배상 범위 |
| P0 | 민법 제396조 | 과실상계 |
| P0 | 자동차손해배상 보장법 제3조 | 자동차 사고 손해배상 책임 |

## 5. 응답 확인 체크리스트

### 법령 목록

- [ ] `민법` 검색 결과가 반환된다.
- [ ] 법령 ID 또는 법령일련번호를 확인할 수 있다.
- [ ] 법령명, 약칭, 시행일자, 상세 링크를 확인할 수 있다.

### 법령 본문

- [ ] 법령 본문을 JSON 또는 XML로 받을 수 있다.
- [ ] 조문 번호와 조문 본문을 추출할 수 있다.
- [ ] `민법_제750조` 같은 `normalized_ref`를 만들 수 있다.

### 판례 목록

- [x] `손해배상` 본문 검색 결과가 반환된다.
- [ ] 판례일련번호를 확인할 수 있다.
- [ ] 사건명, 사건번호, 선고일자, 법원명, 판례상세링크를 확인할 수 있다.
- [x] `display`, `page`, `sort`가 예상대로 동작한다.

### 판례 상세

- [ ] 판례일련번호로 상세 원문을 조회할 수 있다.
- [ ] 판시사항, 판결요지, 참조조문, 판례내용을 확인할 수 있다.
- [ ] 원문 HTML 또는 텍스트 정리가 가능한 구조인지 확인한다.

### P0 조문별 판례 검색

- [ ] 각 P0 조문 query가 검색 결과를 반환한다.
- [ ] 검색 결과 수가 MVP 수집 목표인 300~500건에 충분한지 추정한다.
- [ ] 중복 가능성이 높은 사건번호/선고일자/법원명 조합을 확인한다.

## 6. 내부 DB 매핑 초안

### `laws`

| API 필드 후보 | DB 필드 |
|---------------|---------|
| 법령ID 또는 법령일련번호 | `law_code` |
| 법령명한글 | `official_name` |
| 법령약칭명 | `short_name` |
| 시행일자 | `effective_date` |
| 법령상세링크 | `source_url` |

### `articles`

| API 필드 후보 | DB 필드 |
|---------------|---------|
| 조문번호 | `article_no` |
| 조문가지번호 | `article_branch_no` |
| 항번호 | `paragraph_no` |
| 호번호 | `subparagraph_no` |
| 조문제목 | `title` |
| 조문내용 | `body` |
| 법령명 + 조문번호 | `normalized_ref` |
| 시행일자 | `effective_date` |

### `cases`

| API 필드 후보 | DB 필드 |
|---------------|---------|
| 판례일련번호 | `external_id` |
| 사건번호 | `case_no` |
| 법원명 | `court_name` |
| 법원종류코드 | `court_level` |
| 선고일자 | `decision_date` |
| 사건명 | `case_name` |
| 사건종류명 | `case_type` |
| 판례상세링크 | `source_url` |
| 판례내용 | `raw_text` |
| 원 응답 | `raw_html` 또는 raw JSON 저장소 |

### 중복 기준

1. `case_no + decision_date + court_name`
2. `source_hash`

## 7. 실패 처리 기준

- API 인증 오류: `.env`의 `LAW_API_OC` 값을 다시 확인한다.
- 네트워크 오류: 같은 명령을 재실행하고, 실패 로그를 남긴다.
- JSON 파싱 실패: 원문 텍스트를 그대로 저장하고 응답 `type=XML`도 시험한다.
- 판례 상세 누락: 목록 row는 버리지 않고 재처리 대상으로 표시한다.
- 조문 검색 결과 부족: P1 조문과 키워드 검색을 추가한다.

## 8. 다음 구현 작업

샘플 호출이 확인되면 다음 순서로 구현한다.

1. 응답 JSON 구조를 기준으로 `collect_laws` 필드 매핑 확정
2. P0 조문별 판례 수를 기록
3. `collect_cases`의 pagination 전략 확정
4. raw response 저장 위치와 `source_hash` 계산 방식 확정
5. DB migration 작성

## 9. 2026-06-03 샘플 호출 결과

실행 명령:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_law_api_probe.ps1
```

저장 위치:

```text
data/api_samples/
```

확인 결과:

| 항목 | 결과 |
|------|------|
| 법령 목록 조회 | 성공, `민법` 검색 결과 6건 |
| 법령 본문 조회 | 성공, 응답 root에 `기본정보`, `조문`, `부칙`, `제개정이유` 포함 |
| 판례 목록 조회 | 성공, `손해배상` 본문 검색 결과 16,749건 |
| 판례 상세 조회 | 성공, `판시사항`, `판결요지`, `참조조문`, `판례내용`, `판례정보일련번호` 포함 |
| 인증값 저장 | `.env` 사용 |
| 인증값 마스킹 | 저장 샘플의 요청 URL과 응답 내부 상세링크 모두 `OC=***` 처리 |

P0 조문별 판례 본문 검색 결과:

| 조문 query | 검색 결과 수 |
|------------|--------------|
| 민법 제750조 | 1,020 |
| 민법 제751조 | 195 |
| 민법 제763조 | 207 |
| 민법 제393조 | 254 |
| 민법 제396조 | 286 |
| 자동차손해배상 보장법 제3조 | 669 |

확인된 구현 포인트:

- 판례 목록의 `id`는 검색 결과 순번이고, 상세 조회에는 `판례일련번호`를 사용해야 한다.
- 법령 목록 검색은 `민법` query에서 `난민법`도 함께 반환되므로, `법령명한글 == "민법"` exact match를 우선 적용한다.
- 판례 상세 `판례내용`에는 `<br/>`이 포함되므로 normalize 단계에서 HTML 제거와 문단 분리가 필요하다.
- `display`는 샘플에서 5건으로 제한했으며, 실제 수집에서는 `display=100`, `page=1..N` 전략을 사용한다.

## 10. 2026-06-03 pagination 확인 결과

실제 page 2 호출:

```text
lawSearch.do
target=prec
query=민법 제750조
search=2
display=5
page=2
sort=ddes
```

응답 요약:

```json
{
  "page": "2",
  "totalCnt": "1020",
  "itemCount": 5,
  "firstId": "6",
  "firstCaseNo": "2023나2013051",
  "firstSerial": "617233"
}
```

확정 사항:

- 목록 API pagination은 `display`와 `page` 파라미터로 제어한다.
- 응답 root는 판례 검색에서 `PrecSearch`, 법령 검색에서 `LawSearch`다.
- 현재 페이지는 응답의 `page` 문자열로 확인한다.
- 전체 건수는 `totalCnt` 문자열을 정수로 변환해 사용한다.
- 판례 목록의 `id`는 페이지 내 또는 검색 결과 순번이며 상세 조회 키가 아니다.
- 판례 상세 조회 키는 `판례일련번호`다.
- `has_next`는 `page * display < totalCnt`로 계산한다.

수집 기본값:

```text
display=100
page=1..ceil(totalCnt/display)
sort=ddes
search=2
```

MVP에서는 조문별 목표 수집량을 채우면 다음 page 호출을 중단할 수 있다.

## 11. `collect_laws` 설계 확정

목표:

- MVP 조문 범위의 법령, 약칭, 조문 본문을 내부 DB에 적재한다.
- 런타임 조문 정규화가 외부 API 없이 `laws`, `law_aliases`, `articles`만으로 동작하게 한다.

입력:

```text
docs/StatuteScope.md의 P0/P1 조문 목록
LAW_API_OC
LAW_API_BASE_URL
```

처리 흐름:

```text
1. 조문 목록에서 법령명 단위로 dedupe
2. lawSearch.do target=eflaw query={법령명} 호출
3. 법령명 exact match 우선으로 법령 row 선택
4. lawService.do target=eflaw ID={법령ID} 또는 MST 기반 상세 조회
5. 조문 배열에서 필요한 article_no 추출
6. normalized_ref 생성
7. laws, law_aliases, articles upsert
8. pipeline_runs에 성공/실패 수 기록
```

정규화 규칙:

```text
법령명: 공백 trim, 괄호 설명 제거 없음
조문번호: 제750조 → 750
가지번호: 제750조의2 → article_no=750, article_branch_no=2
normalized_ref: {공식법령명}_제{article_no}조[의{branch_no}]
예: 민법_제750조
```

DB upsert key:

```text
laws: law_code 또는 official_name + effective_date
law_aliases: law_id + alias
articles: law_id + article_no + article_branch_no + paragraph_no + subparagraph_no + effective_date
```

기본 alias:

```text
official_name
short_name
공백 제거 법령명
자주 쓰는 약칭 수동 목록
```

실패 처리:

- exact match가 없으면 후보 목록을 raw로 저장하고 `needs_review` 성격의 로그를 남긴다.
- 조문 본문 추출 실패 시 법령 row는 저장하고 article은 재처리 대상으로 남긴다.
- API 응답 JSON 파싱 실패 시 raw text를 파일로 저장하고 XML 재시도 후보로 기록한다.

CLI 초안:

```powershell
python -m pipelines.collect_laws --scope damages --priority P0
python -m pipelines.collect_laws --scope damages --priority P0,P1
```

출력 요약:

```json
{
  "stage": "collect_laws",
  "laws_upserted": 2,
  "articles_upserted": 11,
  "aliases_upserted": 6,
  "failed_items": []
}
```

## 12. `collect_cases` 설계 확정

목표:

- P0/P1 조문과 보완 키워드로 손해배상 판례 300~500건을 수집한다.
- 목록 row, 상세 원문, raw response, 중복 제거 키를 안정적으로 남긴다.

입력:

```text
docs/StatuteScope.md의 조문 목록
docs/StatuteScope.md의 수집 키워드
LAW_API_OC
limit
display
```

처리 흐름:

```text
1. collect_laws 완료 여부 확인
2. 조문 query 생성: 민법 제750조, 민법 제396조 ...
3. 키워드 query 생성: 교통사고 손해배상, 과실상계 손해배상 ...
4. lawSearch.do target=prec search=2 display=100 page=N sort=ddes 호출
5. totalCnt와 page로 has_next 계산
6. 각 목록 row의 판례일련번호 dedupe
7. lawService.do target=prec ID={판례일련번호} 상세 조회
8. cases raw row upsert
9. query와 판례일련번호 연결 메타 저장
10. 목표 수집량 또는 page limit 도달 시 종료
```

수집 query 우선순위:

```text
1. P0 조문 query
2. P0 조문 + 손해배상 보강 query
3. P1 조문 query
4. 손해배상 도메인 키워드 query
```

pagination 정책:

```text
display=100
page 시작값=1
has_next = page * display < totalCnt
조문별 max_pages 기본값=20
전체 limit 기본값=500
```

상세 조회 정책:

```text
목록 row의 판례일련번호를 상세 ID로 사용
상세 조회 실패 시 목록 row와 실패 상태를 저장
동일 판례일련번호는 중복 상세 호출하지 않음
```

중복 제거:

```text
1차: external_id = 판례일련번호
2차: case_no + decision_date + court_name
3차: source_hash(raw_text 또는 상세 raw response 기반)
```

저장 필드:

```text
cases.external_id        ← 판례일련번호
cases.case_no            ← 사건번호
cases.court_name         ← 법원명
cases.decision_date      ← 선고일자 YYYY-MM-DD 변환
cases.case_name          ← 사건명
cases.case_type          ← 사건종류명
cases.source_url         ← 판례상세링크 또는 공식 상세 URL
cases.raw_text           ← 판례내용
cases.raw_html           ← 상세 raw response 또는 HTML 포함 원문
cases.source_hash        ← normalized raw_text hash
```

필터링:

- 사건종류명 `민사`를 우선한다.
- 사건명 또는 판례내용에 손해배상 관련성이 낮으면 저장하되 후속 extract 단계에서 낮은 우선순위로 둔다.
- 원문이 없거나 판례내용이 비어 있으면 재처리 대상으로 남긴다.

CLI 초안:

```powershell
python -m pipelines.collect_cases --scope damages --priority P0 --limit 300 --display 100
python -m pipelines.collect_cases --scope damages --priority P0,P1 --limit 500 --display 100
python -m pipelines.collect_cases --query "교통사고 손해배상" --limit 100
```

출력 요약:

```json
{
  "stage": "collect_cases",
  "queries_run": 6,
  "list_rows_seen": 1200,
  "unique_case_ids": 430,
  "details_fetched": 430,
  "cases_upserted": 420,
  "duplicates_skipped": 10,
  "failed_items": []
}
```

## 13. 다음 구현 연결

`collect_laws`와 `collect_cases` 구현 전에 필요한 DB migration:

```text
pipeline_runs
laws
law_aliases
articles
cases
```

초기 구현은 raw 적재까지만 완료하고, HTML 제거와 문단 분리는 다음 단계인 `normalize`, `split`에서 처리한다.
