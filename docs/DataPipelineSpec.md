# 데이터 파이프라인 명세

## 1. 목표

처음에는 300~500건을 안정적으로 넣고, 나중에 수만 건 이상으로 확장할 수 있는 데이터 파이프라인을 만든다. 핵심은 모든 단계가 독립 실행 가능하고, 실패해도 재처리할 수 있는 구조다.

법령정보센터 API는 서비스 런타임 백엔드에 붙이지 않는다. 로컬 또는 배치 파이프라인에서만 호출해 DB를 채우는 용도로 사용한다. 런타임 검색 API는 내부 DB만 조회한다.

## 2. 전체 파이프라인

```text
collect
→ normalize
→ split
→ extract
→ structure
→ validate
→ embed
→ load/index
→ evaluate
```

## 3. 단계별 역할

### collect

역할:

- 법령정보센터 API에서 법령, 조문, 판례 목록 수집
- 판례 상세 원문 수집
- raw_text, raw_html, source_url 저장

입력:

- 조문 목록
- 검색 키워드
- 페이지 범위

출력:

- `cases` raw row
- `laws` row
- `articles` row
- `law_aliases` row
- `source_hash`

중복 기준:

- `case_no + decision_date + court_name`
- `source_hash`

### normalize

역할:

- HTML 제거
- 공백 정리
- 특수문자 정리
- 사건번호, 법원, 선고일 정규화

출력:

- 정리된 `raw_text`
- normalized metadata

### split

역할:

- 원문을 문단 단위로 분리
- 섹션 타입 추정
- char offset 저장

section_type:

- `facts`
- `issue`
- `reasoning`
- `order`
- `claim`
- `unknown`

출력:

- `case_paragraphs`

### extract

역할:

- 규칙 기반 조문 추출
- 법원명, 사건유형, 도메인 추정
- 결과 후보 추출
- 키워드 추출

규칙 기반으로 처리 가능한 부분은 LLM보다 먼저 처리한다.

### structure

역할:

- LLM으로 판례를 구조화한다.
- facts, issue, reasoning, conclusion을 추출한다.
- material_facts를 추출한다.
- aggravating/mitigating factors를 추출한다.
- key_disputed_facts를 추출한다.
- outcome을 세분화한다.

중요:

- LLM은 원문에 있는 내용만 추출해야 한다.
- 불명확하면 null 또는 unknown을 반환해야 한다.
- 모든 중요 필드는 evidence span을 가져야 한다.

### validate

역할:

- JSON Schema 검증
- 조문 실존 여부 검증
- evidence span 존재 여부 검증
- confidence 계산
- needs_review 분류

needs_review 조건:

- confidence < 0.7
- cited_articles 없음
- outcome direction unknown
- facts evidence 없음
- material_facts가 비어 있음
- LLM output validation 실패

### embed

역할:

- 검색용 텍스트 생성
- 임베딩 생성
- `case_embeddings` 저장

embedding_type:

- facts
- issue
- reasoning
- material_facts
- combined
- paragraph

초기 모델:

- 768차원 단일 모델

모델 변경 시:

- 기존 컬럼에 혼용하지 않는다.
- embedding_dimension과 embedding_model을 기준으로 재임베딩한다.

### load/index

역할:

- PostgreSQL 적재
- pgvector 인덱스 갱신
- GIN 인덱스 활용
- pipeline_runs 업데이트

### evaluate

역할:

- 수집 결과 품질 확인
- 중복률 확인
- 구조화 confidence 확인
- 검색 평가 세트 실행

## 4. CLI 설계

예상 명령:

```bash
python -m pipelines.collect_laws --scope damages
python -m pipelines.collect --domain damages --limit 500
python -m pipelines.normalize --run-id RUN_ID
python -m pipelines.split --run-id RUN_ID
python -m pipelines.extract --run-id RUN_ID
python -m pipelines.structure --run-id RUN_ID --only-needs-llm
python -m pipelines.validate --run-id RUN_ID
python -m pipelines.embed --run-id RUN_ID --model ko-sbert-768
python -m pipelines.evaluate --run-id RUN_ID
```

`collect_laws`는 법령명, 약칭, 조문 본문, normalized_ref를 DB에 채운다. 이후 조문 정규화와 검색 검증은 외부 API가 아니라 내부 DB 기준으로 수행한다.

## 5. 재처리 정책

### 법령/조문 갱신

```text
collect_laws
→ article normalization table 갱신
→ 조문 alias 검증
→ 관련 판례 수집 필요 여부 확인
```

런타임 API에서 법령정보센터 API를 직접 호출하지 않으므로, 법령/조문 최신성은 배치 갱신 주기에 의존한다. UI에는 데이터 기준일을 표시한다.

### 조문 목록 추가

```text
collect
→ normalize
→ split
→ extract
→ structure
→ validate
→ embed
```

### 프롬프트 변경

```text
structure
→ validate
→ embed material_facts/combined
→ evaluate
```

### 임베딩 모델 변경

```text
embed
→ index
→ evaluate
```

### 파서 오류 수정

```text
normalize 또는 split부터 재실행
```

## 6. 대량 적재 대비

처음부터 다음 정보를 저장해야 한다.

- `source_hash`
- `content_hash`
- `structure_hash`
- `pipeline_run_id`
- `prompt_version`
- `model_name`
- `embedding_model`
- `embedding_dimension`
- `needs_regeneration`

이 정보가 없으면 나중에 어떤 데이터만 다시 처리해야 하는지 알 수 없다.

## 7. 완료 체크리스트

- [ ] 각 단계가 독립 실행 가능하다.
- [ ] 실패 데이터가 버려지지 않는다.
- [ ] source_hash로 중복을 막는다.
- [ ] LLM 구조화 결과에 evidence span이 있다.
- [ ] confidence와 needs_review가 계산된다.
- [ ] 임베딩 재생성 대상이 추적된다.
- [ ] 평가 결과가 pipeline run에 연결된다.
