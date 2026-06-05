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

## 9.1 피드백 MVP 운영 기준

현재 DB는 사용자 피드백을 받기 위한 MVP 안정권에 도달했다.

최신 기준:

| 항목 | 값 |
|------|---:|
| 판례 수 | 1,076 |
| 문단 수 | 119,542 |
| 구조화 row | 1,943 |
| 임베딩 row | 9,267 |
| 조문 검색 precision@10 | 1.0 |
| 자연어 Top-5 관련도 | 3.625 |
| 비교 후보 material fact match | 0.836 |
| 비교 후보 domain match | 1.0 |
| 비교 후보 issue tag overlap | 0.778 |
| primary quality issue rate | 0.061 |
| primary missing scope rate | 0.180 |

출시 직후 우선 모니터링할 피드백 label:

| Label | 기준 | 대응 |
|-------|------|------|
| `facts_not_similar` | 30% 초과 | material fact 추출과 비교 랭킹 가중치 점검 |
| `material_fact_missed` | 20% 초과 | `material_facts` rule/LLM 구조화 개선 |
| `wrong_statute` | 15% 초과 | 조문 추출, alias, normalized_ref 보강 |
| `summary_error` | 15% 초과 | RAG fallback 요약과 Gemini evidence prompt 점검 |
| `not_relevant` | 25% 초과 | 자연어 intent parser와 ranking rule 점검 |

출시 직후 피드백은 최소 20~30건이 쌓인 뒤 판단한다. 그 전에는 개별 오류를 기록만 하고, 전체 가중치 조정은 보류한다.

## 9.2 현재 검색 가능 범위

배포 시 사용자에게 안내 가능한 범위:

- 손해배상/불법행위: 교통사고, 과실상계, 위자료, 사용자책임, 공동불법행위, 소멸시효, 손해배상 범위
- 노동: 임금, 퇴직금, 해고, 근로자 지위, 업무상 사고 관련 분쟁
- 부당이득: 반환청구, 법률상 원인 없는 이득, 구상/정산 성격 분쟁
- 임대차: 보증금 반환, 건물명도, 임대차 종료 관련 분쟁
- 조세: 취득세, 부과처분 취소, 경정청구
- 물권/부동산: 소유권이전등기, 말소등기, 부동산 권리분쟁
- 상속/가족: 상속재산, 유류분, 이혼, 위자료, 재산분할
- 계약: 계약대금, 채무불이행, 약정금, 공사대금
- 보험: 보험금, 보험자대위, 구상금

제한적으로만 안내할 범위:

- 보험 전문 쟁점은 DB 건수가 아직 작다.
- 계약, 가족, 상속, IP는 기본 검색은 가능하지만 넓은 공개 서비스 수준의 커버리지는 아니다.
- 형사, 회사/상사, 행정 일반, 지식재산 전반은 아직 full-scope가 아니다.

사용자 노출 문구 권장:

```text
CaseLens는 공개 판례 기반 검색/비교 보조 도구입니다. 결과는 참고용이며 법률 자문이 아닙니다. 중요한 판단에는 원문과 전문가 검토가 필요합니다.
```

## 10. 데이터 보존 정책

MVP에서 최소 결정:

- 공개 판례 원문은 내부 재처리용으로 보존
- 사용자 검색 로그는 기본 90일 보존
- 피드백은 품질 개선용으로 보존
- 개인정보 입력 가능성이 있는 자연어 쿼리는 추후 마스킹 검토

## 11. 완료 체크리스트

- [x] pipeline_runs로 실패 원인을 추적한다.
- [ ] llm_runs로 비용과 실패율을 본다. MVP에서는 Gemini 미설정 시 local fallback으로 운영 가능하다.
- [x] 재구조화와 재임베딩 대상 선별이 가능하다.
- [x] 사용자 노출 오류는 피드백으로 수집된다.
- [x] 법률 고지와 데이터 범위 고지가 유지된다.

## 12. 출시 직전 체크리스트

출시 직전에 아래 명령을 모두 통과시킨다.

```powershell
npm.cmd run api:test
npm.cmd run web:lint
npm.cmd run web:build
npm.cmd run eval:mvp
```

환경 변수 확인:

- `DATABASE_URL`
- `SEARCH_API_URL`
- `NEXT_PUBLIC_APP_URL`
- `EMBEDDING_PROVIDER`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSION`
- `GEMINI_API_KEY`는 선택 사항

UI 확인:

- 검색 결과에 근거 문단 또는 원문 링크가 노출된다.
- 비교 분석에 evidence id/link가 유지된다.
- 참고용/비법률자문 고지가 보인다.
- 피드백 제출 UI가 정상 동작한다.
- review status 또는 confidence가 관리자/검토용으로 확인 가능하다.
