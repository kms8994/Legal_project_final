# 운영과 유지보수 명세

## 1. 목표

MVP 이후 데이터를 계속 늘리고, 프롬프트와 모델을 바꾸고, 오류 데이터를 재처리할 수 있어야 한다.

## 2. 유지보수 핵심 원칙

- 원문은 보존한다.
- 파생 데이터는 재생성 가능하게 만든다.
- 버전과 hash를 남긴다.
- 실패 데이터는 삭제하지 않고 재처리 상태로 둔다.
- 검색 품질 지표를 정기적으로 본다.

## 3. 데이터 추가 절차

```text
새 조문 추가
→ collect 실행
→ normalize/split/extract
→ structure/validate
→ embed
→ evaluate
→ 품질 지표 기록
```

## 4. 재수집 정책

재수집이 필요한 경우:

- 원문 source 변경
- HTML 파서 오류 수정
- 법령 API 응답 변경
- 누락 판례 발견
- 중복 판례 정리

처리:

- 기존 raw row를 덮어쓰기 전에 source_hash 비교
- 변경된 경우 새 pipeline_run_id 기록
- 기존 구조화 결과는 obsolete 상태로 표시 가능

## 5. 재구조화 정책

재구조화가 필요한 경우:

- 프롬프트 변경
- LLM 모델 변경
- material_facts 스키마 변경
- outcome 스키마 변경
- evidence span 검증 로직 변경

처리:

```text
대상 case 선별
→ structure 재실행
→ validate
→ confidence 비교
→ 필요 embedding 재생성
```

## 6. 재임베딩 정책

재임베딩이 필요한 경우:

- 임베딩 모델 변경
- embedding_type 추가
- content_hash 변경
- material_facts 구조 변경

처리:

- 같은 vector 컬럼에 다른 차원을 혼용하지 않는다.
- embedding_model, embedding_dimension 기준으로 조회한다.
- needs_regeneration true 데이터를 배치 처리한다.

## 7. 비용 관리

추적 대상:

- LLM 호출 수
- 목적별 token 사용량
- 월별 cost_usd
- 실패율
- 평균 latency

MVP에서는 결제는 구현하지 않지만, 비용 추적은 반드시 한다.

## 8. 장애 대응

| 장애 | 대응 |
|------|------|
| LLM timeout | fallback 요약/비교 표시 |
| LLM invalid JSON | 1회 재시도 후 fallback |
| DB 검색 지연 | limit 축소, 인덱스 점검 |
| 임베딩 실패 | needs_regeneration 표시 |
| 수집 실패 | pipeline_runs에 실패 사유 기록 |
| evidence 부족 | 사용자 노출 제한, 검수 대상 |

## 9. 모니터링 지표

- 일별 신규 수집 판례 수
- 중복률
- 파싱 실패율
- needs_review 비율
- LLM 실패율
- 검색 p95 latency
- 비교 후보 선택률
- `facts_not_similar` 피드백 비율
- `material_fact_missed` 피드백 비율
- 월별 LLM 비용

## 10. 데이터 보존 정책

MVP에서 최소 결정:

- 공개 판례 원문은 내부 재처리용으로 보존
- 사용자 검색 로그는 기본 90일 보존
- 피드백은 품질 개선용으로 보존
- 개인정보 입력 가능성이 있는 자연어 쿼리는 추후 마스킹 검토

## 11. 완료 체크리스트

- [ ] pipeline_runs로 실패 원인을 추적한다.
- [ ] llm_runs로 비용과 실패율을 본다.
- [ ] 재구조화와 재임베딩 대상 선별이 가능하다.
- [ ] 사용자 노출 오류는 피드백으로 수집된다.
- [ ] 법률 고지와 데이터 범위 고지가 유지된다.

