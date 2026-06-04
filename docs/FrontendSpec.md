# Frontend 구현 명세

## 1. 프론트엔드 목표

프론트엔드는 사용자가 검색에서 비교까지 빠르게 이동하도록 돕는다. MVP는 설명이 많은 랜딩 페이지가 아니라 바로 사용할 수 있는 검색/비교 도구여야 한다.

## 2. 화면 목록

| 화면 | 경로 예시 | 역할 |
|------|----------|------|
| 검색 시작 | `/` | 조문, 자연어, 사건번호 입력 |
| 검색 결과 | `/search` | 판례 카드 목록 |
| 판례 상세 | `/cases/[caseId]` | 구조화 정보와 원문 근거 |
| 비교 후보 | `/cases/[caseId]/compare` | 기준 판례 기준 후보 Top 5 |
| 비교 분석 | `/compare?base=&target=` | 두 판례 비교 |
| 피드백 | 화면 내 컴포넌트 | 관련성/오류 피드백 |

## 3. 컴포넌트 구조

```text
components/
  search/
    SearchInput.tsx
    SearchModeTabs.tsx
    ParsedIntentPanel.tsx
    SearchResultList.tsx
    CaseCard.tsx
  cases/
    CaseHeader.tsx
    CaseStructuredSummary.tsx
    EvidenceParagraph.tsx
    SourceLink.tsx
  compare/
    BaseCaseBanner.tsx
    CompareCandidateList.tsx
    CompareCandidateCard.tsx
    ComparisonMatrix.tsx
    TurningPointList.tsx
    EvidenceLinkedClaim.tsx
  feedback/
    FeedbackBar.tsx
    FeedbackReasonDialog.tsx
  common/
    Disclaimer.tsx
    LoadingState.tsx
    EmptyState.tsx
    ErrorState.tsx
```

## 4. 검색 시작 화면

필수 요소:

- 검색 모드 탭: 조문, 자연어, 사건번호
- 검색 입력
- 검색 버튼
- 짧은 면책 고지
- 데이터 범위 고지

검색 모드별 입력 예:

- 조문: `민법 제750조`
- 자연어: `교통사고 피해자의 과실상계가 문제된 손해배상 판례`
- 사건번호: `2021다12345`

## 5. 검색 결과 화면

필수 요소:

- 사용자가 입력한 검색어
- 자연어 검색일 경우 `이렇게 이해했어요` 패널
- 판례 카드 목록
- 각 카드의 기준 판례 선택 버튼
- 공식 원문 링크
- AI 요약 배지

판례 카드 필드:

- 사건번호
- 법원
- 선고일
- 사건명
- 요약
- 주요 조문
- outcome direction
- key_factor
- relevance score는 내부용이며 기본 노출하지 않는다.
- `원문 근거 보기` 버튼

## 6. 비교 후보 화면

비교 후보 화면은 CaseLens의 핵심 화면이다.

필수 요소:

- 기준 판례 요약
- 후보 Top 5
- 후보별 공통 사실
- 후보별 미세 차이 가능성
- 결과 차이 요약
- 비교하기 버튼
- 관련 없음 피드백

후보 카드에서 강조할 순서:

1. 기준 판례와 얼마나 사실관계가 유사한지
2. 어떤 material facts가 같은지
3. 어떤 작은 차이가 결과를 갈랐을 가능성이 있는지
4. 결과가 어떻게 다른지

## 7. 비교 분석 화면

비교 분석 화면 구성:

```text
상단: 기준 판례 vs 비교 판례 메타 정보
중단 1: 공통 사실관계
중단 2: 핵심 미세 차이
중단 3: 결과 차이
하단: 원문 근거 문단
하단: 피드백
```

비교 매트릭스 예:

| 항목 | 기준 판례 | 비교 판례 | 의미 |
|------|----------|----------|------|
| 사고 유형 | 차량 대 보행자 | 차량 대 보행자 | 공통 |
| 피해자 행위 | 과실 낮게 인정 | 무단횡단 인정 | 분기점 |
| 인과관계 | 인정 | 인정 | 공통 |
| 결과 | 일부 인용 | 과실상계로 감액 | 차이 |

## 8. 판례 상세 화면

필수 요소:

- 판례 메타 정보
- 구조화 사실관계
- 쟁점
- 법원 판단
- 결과
- material facts
- aggravating/mitigating factors가 있는 경우 표시
- 원문 근거 문단
- 공식 원문 링크
- 구조화 confidence
- 검수 전 표시

## 9. 상태 관리

MVP에서는 복잡한 전역 상태를 피한다.

- 검색 쿼리와 결과는 URL query와 서버 응답 중심
- 기준 판례 선택은 URL 또는 route state에 반영
- 비교 대상은 query parameter로 공유 가능하게 구성
- 피드백 제출 상태만 local component state 사용

## 10. 예외 UI

| 상황 | UI 처리 |
|------|---------|
| 조문 파싱 실패 | 입력 예시 표시 |
| 검색 결과 없음 | 조건 완화 제안 |
| 자연어 confidence 낮음 | 추가 사실 입력 요청 |
| 비교 후보 부족 | outcome 조건 완화 결과 표시 |
| LLM timeout | 표 기반 비교 먼저 표시 |
| evidence 부족 | 원문 근거 부족 배지 |

## 11. 완료 체크리스트

- [ ] 첫 화면에서 바로 검색할 수 있다.
- [ ] 검색 결과에서 기준 판례를 선택할 수 있다.
- [ ] 비교 후보 Top 5가 표시된다.
- [ ] 비교 화면에서 공통점, 차이점, 결과 차이가 보인다.
- [ ] 모든 AI 요약에 원문 확인 필요 표시가 있다.
- [ ] 모바일에서 비교 화면이 깨지지 않는다.
- [ ] 피드백 제출이 가능하다.

