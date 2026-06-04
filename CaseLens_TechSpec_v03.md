# CaseLens — 기술 구현 명세서 (Technical Specification)

> 서비스 작동 방식 및 DB 파이프라인 구현 가이드  
> 버전: v0.4 | 작성일: 2025-06 | 보강일: 2026-06-03

---

## 목차

1. [시스템 아키텍처 개요](#1-시스템-아키텍처-개요)
2. [서비스 플로우 구현](#2-서비스-플로우-구현)
   - 2.1 조문 입력 플로우
   - 2.2 자연어 입력 플로우
   - 2.3 판례 비교 플로우
3. [DB 파이프라인 구현](#3-db-파이프라인-구현)
   - 3.1 데이터 수집
   - 3.2 판례 전처리 & 구조화
   - 3.3 임베딩 & 벡터 저장
   - 3.4 유사도 검색
4. [기술 스택 선택 근거](#4-기술-스택-선택-근거)
5. [MVP 구현 범위와 단계별 로드맵](#5-mvp-구현-범위와-단계별-로드맵)
6. [검색/비교 랭킹 설계 상세](#6-검색비교-랭킹-설계-상세)
7. [구조화 스키마 보강](#7-구조화-스키마-보강)
8. [품질 평가 및 검증 기준](#8-품질-평가-및-검증-기준)
9. [데이터 수집 범위와 운영 리스크](#9-데이터-수집-범위와-운영-리스크)
10. [API 명세 (내부)](#10-api-명세-내부)
11. [LLM 프롬프트 설계 상세](#11-llm-프롬프트-설계-상세)
12. [보안 & 비용 관리](#12-보안--비용-관리)
13. [배포 & 인프라 구성](#13-배포--인프라-구성)
14. [구현 의사결정 및 전체 구축 프로세스](#14-구현-의사결정-및-전체-구축-프로세스)
15. [DB 물리 스키마 및 인덱스 설계](#15-db-물리-스키마-및-인덱스-설계)
16. [법령/조문 정규화 정책](#16-법령조문-정규화-정책)
17. [검색 실패 및 예외 UX](#17-검색-실패-및-예외-ux)
18. [LLM 출력 검증 및 안전장치](#18-llm-출력-검증-및-안전장치)
19. [법률 서비스 고지 및 책임 범위](#19-법률-서비스-고지-및-책임-범위)
20. [남은 부족 부분 및 의사결정 사항](#20-남은-부족-부분-및-의사결정-사항)

---

## 1. 시스템 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                         사용자 (Web)                             │
└────────────────────────┬────────────────────────────────────────┘
                         │ 조문 입력 / 자연어 입력
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (Next.js BFF)                   │
└──────┬──────────────────────┬──────────────────────────────────-┘
       │                      │
       ▼                      ▼
┌────────────┐       ┌─────────────────────┐
│ 조문 라우터 │       │  자연어 쿼리 라우터  │
│ (법령 코드  │       │  (LLM Intent Parser) │
│  파싱)     │       └──────────┬──────────┘
└─────┬──────┘                  │
      │                         │ 정규화된 검색 파라미터
      └──────────┬──────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     판례 검색 엔진                                │
│                                                                   │
│   ┌──────────────┐    ┌────────────────┐    ┌────────────────┐  │
│   │  PostgreSQL   │    │  Vector DB     │    │ Elasticsearch  │  │
│   │  (메타데이터) │    │  (pgvector /   │    │ (전문 검색)    │  │
│   │               │    │   Qdrant)      │    │                │  │
│   └──────────────┘    └────────────────┘    └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM 보조 레이어                                │
│   (사실관계 재정제 / 유사도 재순위 / 비교 요약 생성)               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 서비스 플로우 구현

### 2.1 조문 입력 플로우

**목표:** 사용자가 법조문(예: 민법 제750조)을 입력하면 해당 조문이 인용된 판례 목록을 제시

#### 구현 방법

```
사용자 입력: "민법 제750조"
       │
       ▼
┌─────────────────────────────────────────────────────┐
│  조문 파서                                           │
│  - 정규식으로 법령명 + 조문 번호 추출               │
│  - 예: { law: "민법", article: "750", clause: null } │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│  국가법령정보 API 조회                               │
│  - 조문 정식 명칭, 조문 내용 확인 (정합성 검증)     │
│  - API: https://www.law.go.kr/DRF/lawService.do     │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│  판례 DB 쿼리 (PostgreSQL + Elasticsearch)           │
│  SELECT * FROM cases                                 │
│  WHERE cited_articles @> ARRAY['민법_750']           │
│  ORDER BY relevance_score DESC LIMIT 20             │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
        사실관계 요약 + 결과 카드 리스트 표시
        (사용자가 기준 판례 선택)
```

#### 핵심 기술

| 단계 | 기술 | 이유 |
|------|------|------|
| 조문 파싱 | 정규식 (Regex) | 조문 표기법이 한국 법령 표준으로 패턴 일정 |
| 법령 검증 | 국가법령정보 Open API | 공식 데이터, 무료 |
| 판례 조회 | PostgreSQL `GIN 인덱스` + `@>` 배열 연산 | 조문 코드가 정형화된 메타데이터이므로 벡터 불필요 |
| 결과 카드 요약 | Claude API (Haiku / 경량 모델) | 원문 사실관계 3~4줄 요약 |

---

### 2.2 자연어 입력 플로우

**목표:** "교통사고로 상해를 입었는데 상대방이 보험이 없는 경우" 같은 자연어를 정규화된 검색 파라미터로 변환

#### 구현 방법

```
사용자 입력: "교통사고로 상해를 입었는데 상대방이 보험이 없어요"
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│  LLM Intent Parser  (Claude API — claude-haiku)                  │
│                                                                    │
│  System Prompt:                                                    │
│  "아래 입력을 판례 검색용 JSON으로 변환하라.                       │
│   - case_type: [민사|형사|행정|헌법|가사]                         │
│   - keywords: string[]  (핵심 법률 개념)                          │
│   - legal_issue: string (쟁점 1문장 요약)                         │
│   - inferred_articles: string[] (관련 법조문 추정, 없으면 [])     │
│   - facts_summary: string (사실관계 요약)"                        │
│                                                                    │
│  Output:                                                           │
│  {                                                                 │
│    "case_type": "민사",                                            │
│    "keywords": ["교통사고", "손해배상", "무보험"],                 │
│    "legal_issue": "무보험 차량 교통사고 손해배상 책임",            │
│    "inferred_articles": ["민법 제750조", "자배법 제3조"],          │
│    "facts_summary": "교통사고로 인한 신체 상해, 가해자 무보험"     │
│  }                                                                 │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────┐
        │  Hybrid Search                   │
        │  1. keywords → Elasticsearch     │
        │  2. facts_summary → Vector DB    │
        │  3. inferred_articles → PG 메타  │
        │  → RRF(Reciprocal Rank Fusion)로 │
        │    3개 결과 통합 정렬             │
        └──────────────┬───────────────────┘
                       │
                       ▼
              판례 후보 리스트 제시
              (사용자가 기준 판례 선택)
```

#### 핵심 기술

| 단계 | 기술 | 이유 |
|------|------|------|
| 자연어 파싱 | Claude Haiku API (structured output) | 법률 도메인 한국어 이해도 높음, 빠르고 저렴 |
| 키워드 검색 | Elasticsearch BM25 | 정확한 법률 용어 매칭에 강함 |
| 의미 검색 | pgvector / Qdrant | 유사 사실관계 벡터 유사도 검색 |
| 결과 병합 | RRF (Reciprocal Rank Fusion) | 서로 다른 검색 결과 공정하게 통합 |

---

### 2.3 판례 비교 플로우

**목표:** 기준 판례 선택 → 사실관계 유사 + 결과 상이한 판례 제시 → 선택 시 나란히 비교

#### 구현 방법

```
기준 판례 선택됨 (case_id: ABC123)
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│  유사 판례 검색 (결과 상이 필터 포함)                             │
│                                                                    │
│  1단계: Vector DB에서 사실관계 유사도 상위 50개 후보 추출         │
│         (가중치 적용 — 아래 벡터 필드 참조)                       │
│                                                                    │
│  2단계: 후보 50개 중 기준 판례와 outcome이 다른 것만 필터         │
│         outcome: { 인용/기각/파기환송/원심확정 ... }              │
│                                                                    │
│  3단계: LLM 재순위 (선택적, 상위 10개만)                          │
│         "아래 두 판례의 사실관계 유사도와                          │
│          법적 쟁점 차이를 0~1 점수로 평가하라"                    │
│         → 점수 기반 최종 정렬                                      │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
              유사 판례 카드 리스트 (최대 5개)
              사용자가 비교 대상 선택
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  비교 뷰 생성                                                     │
│  - 두 판례를 구조화된 필드로 나란히 표시                          │
│  - Claude API: 차이점 하이라이트 + 비교 요약 생성                │
│    "두 판례의 사실관계 공통점, 법적 판단 차이, 핵심 분기점 설명" │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. DB 파이프라인 구현

### 3.1 데이터 수집

#### 수집 소스 및 API

| 소스 | API / 방법 | 수집 가능 범위 |
|------|-----------|--------------|
| 국가법령정보센터 | `law.go.kr` Open API (무료, 인증키 필요) | 대법원 판례 전수, 헌재 결정 |
| 대법원 종합법률정보 | `glaw.scourt.go.kr` 크롤링 (robots.txt 확인 필수) | 하급심 일부 |
| 헌법재판소 | `헌재 판례 검색 Open API` | 헌재 결정 전수 |

#### 수집 파이프라인

```python
# 수집 스케줄러 (Apache Airflow 또는 cron)
# 1. 최초 full-load: 법령 API → 전체 판례 수집
# 2. 이후 incremental: 주 1회 신규 판례만 수집

class CaseCrawler:
    def fetch_cases_by_article(self, law_code: str, article: str):
        """법령 코드 + 조문 기준 판례 목록 조회"""
        params = {
            "OC": API_KEY,
            "target": "prec",
            "type": "XML",
            "query": f"{law_code} 제{article}조",
            "display": 100,
            "page": 1
        }
        # https://www.law.go.kr/DRF/lawSearch.do

    def fetch_case_detail(self, case_serial: str):
        """판례 상세 원문 조회"""
        # 사실관계, 판단 이유, 결론, 인용 조문 추출
```

---

### 3.2 판례 전처리 & 구조화

**핵심 과제:** 판례 원문은 비정형 자연어이므로, LLM으로 구조화된 JSON 스키마로 변환

#### 판례 구조화 스키마

```json
{
  "case_id": "대법원-2021다12345",
  "court": "대법원",
  "date": "2022-03-15",
  "case_type": "민사",
  "outcome": "파기환송",
  "cited_articles": ["민법_750", "민법_751", "자배법_3"],

  "structured": {
    "facts": "원고는 2020년 피고 운전 차량에 치여...",
    "facts_keywords": ["교통사고", "손해배상", "과실"],
    "legal_issue": "무보험 차량 운전자의 손해배상 책임 범위",
    "court_reasoning": "피고는 자동차손해배상보장법 제3조에 따라...",
    "conclusion": "원심 판결 파기, 손해배상액 재산정 명령"
  },

  "embeddings": {
    "facts_vector": [...],           // 사실관계 임베딩
    "legal_issue_vector": [...],     // 쟁점 임베딩
    "conclusion_vector": [...],      // 결론 임베딩
    "full_text_vector": [...]        // 전문 임베딩 (보조)
  }
}
```

#### 구조화 파이프라인

```
원문 판례 텍스트
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  1단계: 규칙 기반 파서 (빠름, 저비용)                       │
│  - 정규식으로 "【사실관계】", "【판단】", "【결론】" 섹션   │
│    헤더 추출 (대부분의 판례에 표준 헤더 존재)               │
│  - 조문 코드 추출: "민법 제750조" → "민법_750"             │
│  - 법원명, 선고일, 사건번호 파싱                            │
└─────────────────────┬───────────────────────────────────────┘
                      │ 파싱 실패 or 비정형 판례 (약 20~30%)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  2단계: LLM 구조화 (claude-haiku, 배치 처리)               │
│  - 규칙 기반으로 처리 못한 판례에만 적용 (비용 최소화)     │
│  - Prompt: "아래 판례 원문에서 사실관계/쟁점/결론 추출"    │
│  - 신뢰도 점수 함께 반환 → 낮으면 인간 검수 큐로 이동     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
              구조화된 JSON → PostgreSQL 저장
```

---

### 3.3 임베딩 & 벡터 저장

#### 임베딩 모델 선택

| 모델 | 특징 | 추천 용도 |
|------|------|----------|
| `ko-sbert-multitask` | 한국어 특화 SBERT, 오픈소스 | 사실관계 의미 임베딩 (주력) |
| `text-embedding-3-small` (OpenAI) | 다국어, 빠름, API | 보조 / 정확도 비교용 |
| `bge-m3` | 다국어 M3 임베딩, 오픈소스 | 긴 판례 전문 임베딩 |

> **권장:** 사실관계 필드는 `ko-sbert` 계열 모델을 자체 호스팅하여 비용 절감.  
> 전문 임베딩은 `bge-m3` (최대 8192 토큰 지원, 판례 원문 길이 대응 가능)

#### 벡터 DB 구성

```
# 옵션 A: PostgreSQL + pgvector (단순, 규모 작을 때 권장)
# - 기존 PostgreSQL에 확장만 추가 → 운영 부담 최소
# - 벡터 검색 + 메타 필터를 단일 쿼리로 처리 가능
# - 수백만 건까지 충분

CREATE EXTENSION vector;

CREATE TABLE case_vectors (
    case_id     TEXT PRIMARY KEY,
    facts_vec   vector(768),      -- ko-sbert 출력 차원
    issue_vec   vector(768),
    outcome     TEXT,
    case_type   TEXT,
    court       TEXT,
    date        DATE
);

CREATE INDEX ON case_vectors
  USING ivfflat (facts_vec vector_cosine_ops)
  WITH (lists = 100);

# 옵션 B: Qdrant (수천만 건 이상, 고성능 필요 시)
# - 필터링 + 벡터 검색 동시에 최적화
# - 별도 서비스로 운영
```

---

### 3.4 유사도 검색 (가중치 설계)

사실관계가 유사한 판례를 찾기 위한 **다중 필드 가중치 코사인 유사도**

#### 가중치 설정

```python
SIMILARITY_WEIGHTS = {
    "facts_vector":        0.50,   # 사실관계 — 최고 가중치 (핵심 기준)
    "legal_issue_vector":  0.30,   # 법적 쟁점 — 두 번째 (무엇이 다투어졌는가)
    "cited_articles":      0.15,   # 인용 조문 — 같은 법조문 적용 여부
    "full_text_vector":    0.05,   # 전문 — 보조 (노이즈 많아 낮게 설정)
}

def weighted_similarity(base_case, candidate_case) -> float:
    score = 0.0
    for field, weight in SIMILARITY_WEIGHTS.items():
        if field == "cited_articles":
            # 조문 겹침 비율 (Jaccard)
            intersection = len(set(base_case[field]) & set(candidate_case[field]))
            union = len(set(base_case[field]) | set(candidate_case[field]))
            score += weight * (intersection / union if union > 0 else 0)
        else:
            # 코사인 유사도
            score += weight * cosine_similarity(
                base_case[field], candidate_case[field]
            )
    return score
```

#### pgvector 쿼리 예시

```sql
-- 기준 판례와 사실관계 유사 + 결과 상이 판례 검색
SELECT
    c.case_id,
    c.outcome,
    -- 가중 유사도 점수
    (0.50 * (1 - (v.facts_vec <=> $1::vector))
   + 0.30 * (1 - (v.issue_vec <=> $2::vector))) AS similarity_score
FROM case_vectors v
JOIN cases c ON v.case_id = c.case_id
WHERE
    c.outcome != $3                          -- 결과 상이 필터
    AND c.case_type = $4                     -- 같은 사건 유형
    AND c.case_id != $5                      -- 자기 자신 제외
ORDER BY similarity_score DESC
LIMIT 50;
```

---

## 4. 기술 스택 선택 근거

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer           │  선택 기술              │  역할               │
├──────────────────┼─────────────────────────┼─────────────────────┤
│  Frontend        │  Next.js 14 + TypeScript│  UI, SSR            │
│  BFF/API         │  Next.js API Routes     │  라우팅, 인증        │
│  조문 파서       │  정규식 (Node.js)        │  조문 코드 추출      │
│  자연어 파서     │  Claude Haiku API        │  Intent 정규화       │
│  키워드 검색     │  Elasticsearch 8.x       │  BM25 전문 검색      │
│  벡터 검색       │  pgvector (초기)         │  의미 유사도 검색    │
│                  │  → Qdrant (스케일업 시)  │                      │
│  RDB             │  PostgreSQL 16           │  메타데이터, 관계    │
│  캐시            │  Redis                   │  검색 결과 캐싱      │
│  임베딩          │  ko-sbert (자체 호스팅)  │  한국어 판례 임베딩  │
│  LLM 보조        │  Claude Haiku            │  구조화, 재순위      │
│  비교 요약       │  Claude Sonnet           │  고품질 비교 분석    │
│  데이터 수집     │  Python + Airflow        │  판례 수집 파이프라인│
│  인프라          │  AWS (ECS, RDS, S3)      │  서울 리전           │
└─────────────────────────────────────────────────────────────────┘
```

**LLM 2단계 전략 (비용 최적화)**

```
경량 모델 (Claude Haiku)         고성능 모델 (Claude Sonnet)
────────────────────────         ──────────────────────────
✓ 자연어 → 구조화 파싱           ✓ 판례 간 비교 분석 요약
✓ 판례 원문 구조화 (배치)        ✓ 차이점 하이라이트 생성
✓ 유사도 재순위 (상위 10개)      ✓ 사용자에게 직접 노출되는 결과
✓ 간단한 사실관계 요약           
→ 건당 비용 최소화               → 품질이 직접 UX에 영향
```

---

## 5. MVP 구현 범위와 단계별 로드맵

새로 구축하는 서비스라도 모든 구성 요소를 한 번에 구현하면 개발 범위가 과도하게 커질 수 있다. CaseLens는 검색 품질을 빠르게 검증할 수 있도록 **MVP → 확장 → 운영 고도화** 순서로 나누어 구축한다.

### 5.1 MVP 범위

**목표:** 사용자가 조문 또는 자연어로 판례 후보를 찾고, 기준 판례와 비교 판례의 사실관계/쟁점/결과 차이를 확인할 수 있는 최소 제품을 완성한다.

| 영역 | MVP 포함 | MVP 제외 |
|------|----------|----------|
| Frontend | Next.js 기반 검색/결과/비교 UI | 고급 대시보드, 관리자 검수 UI 전체 |
| API | Next.js API Routes 또는 별도 FastAPI 검색 API | 마이크로서비스 분리 |
| DB | PostgreSQL + pgvector | Qdrant, Elasticsearch 클러스터 운영 |
| 검색 | 조문 검색, 자연어 검색, 기준 판례 기반 유사 판례 검색 | 대규모 RRF 튜닝, 개인화 검색 |
| 데이터 | law.go.kr 기반 대법원/주요 고등법원 판례 우선 수집 | 전체 하급심 포괄 수집 |
| 구조화 | 규칙 기반 파서 + 일부 LLM 보정 | 전량 LLM 구조화 |
| LLM | 자연어 intent 파싱, 판례 카드 요약, 비교 요약 | 실시간 장문 법률 의견 생성 |
| 평가 | 테스트 쿼리 세트 기반 Top-k 평가 | 자동 재학습 파이프라인 |

### 5.2 단계별 로드맵

| 단계 | 목표 | 주요 산출물 |
|------|------|-------------|
| Phase 0: 데이터 기반 구축 | 판례 수집/정규화/구조화 가능성 검증 | 수집 스크립트, 구조화 JSON, 샘플 DB |
| Phase 1: 검색 MVP | 조문/자연어 입력으로 관련 판례 검색 | 검색 API, pgvector 인덱스, 결과 카드 UI |
| Phase 2: 비교 MVP | 기준 판례와 비교 판례의 차이 표시 | 비교 후보 추천, 비교 뷰, LLM 비교 요약 |
| Phase 3: 품질 개선 | 검색 정확도와 구조화 신뢰도 개선 | 평가 세트, 피드백 반영, outcome 세분화 |
| Phase 4: 확장 | 데이터/트래픽 증가 대응 | Elasticsearch, Redis, Qdrant, Airflow 도입 검토 |

### 5.3 초기 도메인 제한

전체 법률 영역을 처음부터 다루면 데이터 품질 검증이 어렵다. MVP는 다음처럼 사용 빈도가 높고 사실관계 비교가 쉬운 도메인부터 시작한다.

1. 임대차: 보증금 반환, 계약갱신, 대항력, 우선변제권
2. 임금/근로: 임금체불, 근로자성, 퇴직금, 해고
3. 손해배상: 교통사고, 불법행위, 과실상계
4. 부당이득/채무불이행: 계약 해제, 반환 청구, 이행 지체

---

## 6. 검색/비교 랭킹 설계 상세

### 6.1 자연어 검색 점수 계산

자연어 검색은 단일 검색 방식보다 여러 신호를 조합해야 한다. 초기에는 아래 가중치를 기본값으로 두고, 평가 결과에 따라 조정한다.

```python
NATURAL_SEARCH_WEIGHTS = {
    "bm25_keyword_score":       0.35,  # 법률 용어 직접 매칭
    "facts_vector_score":       0.30,  # 사실관계 의미 유사도
    "issue_vector_score":       0.15,  # 법적 쟁점 유사도
    "statute_match_score":      0.10,  # 검증된 관련 조문 일치
    "case_type_match_score":    0.10,  # 민사/형사/행정 등 유형 일치
}

def natural_search_score(candidate):
    return (
        0.35 * normalize(candidate.bm25_keyword_score)
      + 0.30 * candidate.facts_vector_score
      + 0.15 * candidate.issue_vector_score
      + 0.10 * candidate.statute_match_score
      + 0.10 * candidate.case_type_match_score
    )
```

### 6.2 조문 검색 점수 계산

조문 검색은 의미 검색보다 **정확한 조문 매칭**이 우선이다. 다만 같은 조문을 인용한 판례가 많을 수 있으므로 쟁점/사실관계 신호를 보조로 사용한다.

```python
STATUTE_SEARCH_WEIGHTS = {
    "exact_article_match":      0.45,
    "same_law_near_article":    0.15,
    "bm25_context_score":       0.20,
    "issue_vector_score":       0.10,
    "recency_or_court_weight":  0.10,
}
```

### 6.3 비교 후보 점수 계산

CaseLens의 핵심 가치는 **사실관계는 유사하지만 결론이나 판단 요소가 다른 판례**를 찾는 것이다. 따라서 비교 후보 점수에는 유사도와 대비도를 함께 넣는다.

```python
COMPARISON_SCORE_WEIGHTS = {
    "fact_similarity":          0.40,
    "issue_similarity":         0.20,
    "statute_overlap":          0.15,
    "facet_match":              0.10,
    "outcome_contrast_score":   0.15,
}

def comparison_candidate_score(base, candidate):
    return (
        0.40 * cosine(base.facts_vector, candidate.facts_vector)
      + 0.20 * cosine(base.issue_vector, candidate.issue_vector)
      + 0.15 * jaccard(base.cited_articles, candidate.cited_articles)
      + 0.10 * facet_match_score(base.facets, candidate.facets)
      + 0.15 * outcome_contrast_score(base.outcome, candidate.outcome)
    )
```

`outcome_contrast_score`는 단순히 판결 주문이 다른지만 보지 않고, 결론의 방향과 핵심 분기점이 다른지를 평가한다.

```python
def outcome_contrast_score(base_outcome, candidate_outcome):
    score = 0.0
    if base_outcome["direction"] != candidate_outcome["direction"]:
        score += 0.5
    if base_outcome["key_factor"] != candidate_outcome["key_factor"]:
        score += 0.3
    if base_outcome["claim_result"] != candidate_outcome["claim_result"]:
        score += 0.2
    return score
```

### 6.4 RRF 적용 기준

Elasticsearch와 Vector DB를 함께 사용할 때는 점수 스케일이 다르므로 raw score를 직접 더하지 않는다. 초기에는 RRF를 사용해 안정적으로 병합한다.

```python
def rrf_score(rank: int, k: int = 60) -> float:
    return 1 / (k + rank)

final_score = (
    rrf_score(bm25_rank)
  + rrf_score(facts_vector_rank)
  + rrf_score(issue_vector_rank)
  + metadata_boost
)
```

---

## 7. 구조화 스키마 보강

### 7.1 outcome 세분화

단순한 `인용/기각/파기환송` 분류는 비교 서비스에 부족하다. 비교 추천과 교육적 설명을 위해 outcome을 다음처럼 세분화한다.

```json
"outcome": {
  "disposition": "청구기각",
  "direction": "원고 불리",
  "claim_result": "전부 기각",
  "relief_type": "손해배상",
  "amount_claimed": null,
  "amount_awarded": null,
  "ratio_or_percentage": null,
  "key_factor": "입증 부족",
  "confidence": 0.82
}
```

| 필드 | 설명 |
|------|------|
| `disposition` | 주문상 결론: 인용, 기각, 각하, 파기환송 등 |
| `direction` | 어느 당사자에게 유리한지: 원고 유리, 피고 유리, 일부 유리 등 |
| `claim_result` | 전부 인용, 일부 인용, 전부 기각 등 청구 단위 결과 |
| `relief_type` | 손해배상, 보증금 반환, 임금 지급 등 구제 유형 |
| `amount_awarded` | 인정 금액이 있는 경우 |
| `key_factor` | 결과를 가른 핵심 판단 요소 |
| `confidence` | 구조화 신뢰도 |

### 7.2 Structured Facets

벡터 유사도만으로 후보를 찾으면 표현이 비슷하지만 법적으로 다른 판례가 섞일 수 있다. 검색 전에 구조화 facet으로 후보군을 좁힌다.

```json
"facets": {
  "legal_domain": "손해배상",
  "case_type": "민사",
  "key_parties": ["개인", "보험회사"],
  "harm_type": "신체",
  "causal_relation": "직접",
  "contract_relation": false,
  "procedural_stage": "상고심",
  "court_level": "대법원"
}
```

### 7.3 원문 근거 추적

LLM 구조화 결과는 반드시 원문 근거와 연결한다. 사용자에게 표시되는 요약/비교 설명은 원문에서 확인 가능한 문단 또는 offset을 함께 저장한다.

```json
"evidence_spans": {
  "facts": [
    { "paragraph_id": "p12", "start": 0, "end": 138 }
  ],
  "legal_issue": [
    { "paragraph_id": "p4", "start": 15, "end": 92 }
  ],
  "court_reasoning": [
    { "paragraph_id": "p18", "start": 0, "end": 210 }
  ],
  "outcome": [
    { "paragraph_id": "order_1", "start": 0, "end": 48 }
  ]
}
```

### 7.4 구조화 신뢰도와 검수 큐

```python
def needs_human_review(structured_case):
    return (
        structured_case.confidence < 0.7
        or not structured_case.cited_articles
        or structured_case.outcome["direction"] == "unknown"
        or len(structured_case.evidence_spans["facts"]) == 0
    )
```

검수 대상 판례는 검색 결과에서 낮은 가중치로 사용하거나, 관리자 검수 완료 전까지 사용자에게 `검수 전 요약` 표시를 붙인다.

---

## 8. 품질 평가 및 검증 기준

검색 서비스는 기능 구현보다 결과 품질 검증이 중요하다. MVP부터 작은 평가 세트를 만들어 반복 측정한다.

### 8.1 평가 데이터셋

| 세트 | 구성 | 목적 |
|------|------|------|
| 조문 검색 세트 | 주요 조문 30개 + 기대 판례 목록 | 조문 매칭 정확도 검증 |
| 자연어 검색 세트 | 학생 질문형 쿼리 50개 | 자연어 intent/search 품질 검증 |
| 비교 검색 세트 | 기준 판례 30개 + 비교 후보 라벨 | 유사/대비 판례 추천 검증 |
| 구조화 검증 세트 | 원문 판례 100건 수작업 라벨 | LLM/규칙 구조화 정확도 측정 |

### 8.2 핵심 지표

| 기능 | 지표 | MVP 목표 |
|------|------|----------|
| 조문 검색 | Top-10 중 실제 해당 조문 인용 판례 비율 | 80% 이상 |
| 자연어 검색 | Top-5 중 사람이 관련 있다고 판단한 판례 수 | 평균 3건 이상 |
| 비교 후보 | Top-5 중 기준 판례와 쟁점이 같고 결과/분기점이 다른 판례 수 | 평균 2건 이상 |
| 구조화 | facts/issue/outcome 필드 정확도 | 75% 이상 |
| 조문 추출 | 존재하지 않는 조문 생성률 | 3% 이하 |
| 응답 속도 | 검색 API p95 latency | 2.5초 이하 |

### 8.3 피드백 라벨

사용자 피드백은 모델 개선에 바로 활용될 수 있도록 단순 좋아요/싫어요보다 더 구체적으로 받는다.

```json
"feedback": {
  "query_id": "q_123",
  "case_id": "case_456",
  "label": "not_relevant",
  "reason": "facts_not_similar",
  "comment": "쟁점은 비슷하지만 사실관계가 다름"
}
```

권장 라벨:

- `relevant`: 관련 있음
- `not_relevant`: 관련 없음
- `wrong_statute`: 조문 매칭 오류
- `facts_not_similar`: 사실관계 불일치
- `outcome_not_contrasting`: 결과 차이가 의미 없음
- `summary_error`: 요약 오류
- `source_needed`: 원문 근거 부족

---

## 9. 데이터 수집 범위와 운영 리스크

### 9.1 데이터 범위 명시

MVP에서는 데이터 범위를 명확하게 제한하고 UI에도 표시한다.

```text
본 서비스의 MVP 검색 범위는 국가법령정보센터에서 제공하는 대법원 판례 및 일부 공개 판례를 우선 대상으로 합니다. 하급심 판례는 공개 범위와 수집 가능성에 따라 단계적으로 확장합니다.
```

### 9.2 주요 리스크와 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 하급심 판례 부족 | 사실관계 유사 판례 모수 감소 | 대법원/고등법원 중심 MVP, 파트너십 검토 |
| HTML 구조 변경 | 파서 실패 | 원문 저장, 파서 버전 관리, 실패율 모니터링 |
| API 호출 제한 | 수집 속도 저하 | rate limit 준수, 증분 수집, 캐싱 |
| LLM hallucination | 잘못된 조문/요약 생성 | 법령 DB 검증, evidence span 필수화 |
| 임베딩 모델 교체 | 벡터 차원 불일치 | embedding_model/version 저장, 재임베딩 배치 |
| 개인정보/민감정보 | 서비스 신뢰도 저하 | 공개 판례 기준, 필요 시 마스킹 파이프라인 |

### 9.3 운영 모니터링 지표

- 일별 신규 수집 판례 수
- 파싱 실패율
- 구조화 `needs_review` 비율
- LLM 구조화 실패율
- 벡터 검색 latency
- 검색 결과 클릭률
- 비교 후보 선택률
- 사용자 `not_relevant` 피드백 비율

---
## 10. API 명세 (내부)

서비스 플로우를 실제로 구현하려면 프론트엔드와 백엔드가 어떤 엔드포인트로 통신하는지 정의가 필요하다. 아래는 CaseLens 핵심 기능을 구동하는 내부 API 명세다.

### 10.1 조문 검색 API

```
GET /api/v1/search/statute

Query Parameters:
  q          string  (required) "민법 제750조"
  page       int     (default: 1)
  size       int     (default: 20, max: 50)
  sort       string  "relevance" | "date_desc" | "date_asc"

Response 200:
{
  "query": {
    "raw": "민법 제750조",
    "parsed": { "law": "민법", "article": "750", "clause": null },
    "article_title": "불법행위의 내용",
    "article_text": "고의 또는 과실로 인한 위법행위로..."
  },
  "total": 1240,
  "page": 1,
  "results": [
    {
      "case_id": "대법원-2021다12345",
      "court": "대법원",
      "date": "2022-03-15",
      "case_type": "민사",
      "outcome": {
        "disposition": "파기환송",
        "direction": "원고 유리"
      },
      "summary_card": "피고 운전 차량에 의한 교통사고로 원고가 신체 상해를 입었으나...",
      "cited_articles": ["민법_750", "민법_751"],
      "relevance_score": 0.91
    }
  ]
}

Error 400: 조문 파싱 실패 시 { "error": "PARSE_FAILED", "suggestion": "민법 제750조 형식으로 입력해주세요" }
Error 404: 조문이 법령 DB에 존재하지 않을 때
```

---

### 10.2 자연어 검색 API

```
POST /api/v1/search/natural

Request Body:
{
  "query": "교통사고로 상해를 입었는데 상대방이 보험이 없어요",
  "page": 1,
  "size": 20
}

Response 200:
{
  "parsed_intent": {
    "case_type": "민사",
    "keywords": ["교통사고", "손해배상", "무보험"],
    "legal_issue": "무보험 차량 교통사고 손해배상 책임",
    "inferred_articles": ["민법_750", "자배법_3"],
    "inferred_articles_validated": true,
    "facts_summary": "교통사고로 인한 신체 상해, 가해자 무보험"
  },
  "total": 87,
  "results": [ /* 조문 검색과 동일한 판례 카드 구조 */ ],
  "search_method": "hybrid_rrf"
}

Note: parsed_intent는 UX에서 "이렇게 이해했어요" 확인용으로 표시 가능
```

---

### 10.3 비교 후보 추천 API

```
GET /api/v1/cases/:case_id/compare-candidates

Path: case_id — 기준 판례 ID

Query Parameters:
  limit     int     (default: 5, max: 10)
  contrast  string  "direction" | "key_factor" | "any"  (default: "direction")

Response 200:
{
  "base_case": {
    "case_id": "대법원-2021다12345",
    "summary_card": "...",
    "outcome": { "disposition": "파기환송", "direction": "원고 유리", "key_factor": "과실 비율" }
  },
  "candidates": [
    {
      "case_id": "대법원-2019다99887",
      "summary_card": "...",
      "outcome": { "disposition": "청구기각", "direction": "원고 불리", "key_factor": "인과관계 불인정" },
      "similarity_score": 0.83,
      "contrast_score": 0.71,
      "composite_score": 0.78,
      "preview_diff": "피해자 과실 인정 여부에서 분기됨"
    }
  ]
}
```

---

### 10.4 판례 비교 뷰 API

```
POST /api/v1/compare

Request Body:
{
  "base_case_id": "대법원-2021다12345",
  "compare_case_id": "대법원-2019다99887"
}

Response 200:
{
  "base": {
    "case_id": "...",
    "structured": { "facts": "...", "legal_issue": "...", "court_reasoning": "...", "conclusion": "..." },
    "outcome": { ... },
    "facets": { ... }
  },
  "compare": { /* 동일 구조 */ },
  "analysis": {
    "common_points": ["교통사고로 인한 신체 상해", "불법행위 손해배상 청구"],
    "turning_points": [
      {
        "factor": "피해자 과실",
        "base_value": "없음",
        "compare_value": "30% 인정",
        "impact": "과실상계 적용 여부로 인용액 차이 발생"
      }
    ],
    "conclusion_diff": "기준 판례는 전부 인용, 비교 판례는 30% 과실상계 후 일부 인용",
    "generated_by": "claude-sonnet",
    "disclaimer": "본 분석은 AI가 생성한 참고 자료이며 법적 효력이 없습니다."
  },
  "evidence_links": {
    "base": { "facts_span": {...}, "reasoning_span": {...} },
    "compare": { "facts_span": {...}, "reasoning_span": {...} }
  }
}

Note: analysis 생성은 10초 이내 스트리밍 응답으로 처리 권장
```

---

### 10.5 판례 상세 조회 API

```
GET /api/v1/cases/:case_id

Response 200:
{
  "case_id": "대법원-2021다12345",
  "court": "대법원",
  "date": "2022-03-15",
  "case_number": "2021다12345",
  "case_type": "민사",
  "cited_articles": ["민법_750", "민법_751"],
  "structured": { ... },
  "outcome": { ... },
  "facets": { ... },
  "full_text_url": "https://glaw.scourt.go.kr/...",  // 원문 링크
  "structuring_confidence": 0.88,
  "is_reviewed": true
}
```

---

### 10.6 공통 에러 코드

| 코드 | HTTP | 의미 |
|------|------|------|
| `PARSE_FAILED` | 400 | 조문 형식 파싱 실패 |
| `ARTICLE_NOT_FOUND` | 404 | 존재하지 않는 법조문 |
| `CASE_NOT_FOUND` | 404 | 판례 ID 없음 |
| `LLM_TIMEOUT` | 503 | AI 분석 생성 초과 (재시도 가능) |
| `SEARCH_UNAVAILABLE` | 503 | 검색 엔진 일시 장애 |
| `RATE_LIMITED` | 429 | 요청 한도 초과 (Free 플랜) |

---

## 11. LLM 프롬프트 설계 상세

LLM 호출은 프롬프트 품질이 결과물 품질을 결정한다. 각 용도별로 프롬프트 템플릿을 명세하고 버전 관리한다.

### 11.1 자연어 Intent 파싱 프롬프트

```
[시스템 프롬프트 — claude-haiku, 온도 0.0]

당신은 한국 법률 전문 판례 검색 시스템의 쿼리 분석기입니다.
사용자의 자연어 입력을 판례 검색에 최적화된 JSON으로 변환합니다.

규칙:
1. case_type은 반드시 [민사, 형사, 행정, 헌법, 가사] 중 하나. 불명확하면 "민사".
2. keywords는 법률 용어 위주 3~6개. 일상어는 법률 개념으로 변환.
   예) "돈을 못 받았어요" → ["채무불이행", "손해배상", "이행청구"]
3. inferred_articles는 확실한 것만. 불확실하면 빈 배열 반환. 존재하지 않는 조문 생성 금지.
4. facts_summary는 2문장 이내, 육하원칙 구조로.
5. 응답은 반드시 JSON만. 설명, 마크다운 불필요.

출력 스키마:
{
  "case_type": string,
  "keywords": string[],
  "legal_issue": string,
  "inferred_articles": string[],
  "facts_summary": string,
  "confidence": number  // 0~1, 파싱 신뢰도
}

[사용자 입력]
{user_query}
```

---

### 11.2 판례 구조화 프롬프트 (배치 전처리)

```
[시스템 프롬프트 — claude-haiku, 온도 0.0, 배치]

당신은 한국 법원 판례 원문을 구조화된 데이터로 변환하는 전문가입니다.

지시:
1. 아래 판례 원문에서 지정된 필드를 추출하라.
2. 원문에 명시된 내용만 사용. 추론/추가 해석 금지.
3. 불명확한 필드는 null 반환. 없는 내용을 만들어내지 마라.
4. facts는 【사실의 인정】또는 【이유】섹션의 첫 사실관계 부분.
5. court_reasoning은 법원의 판단 근거. 원고/피고 주장과 구분.
6. outcome.key_factor는 판결을 가른 핵심 법리 또는 사실 1가지.

출력 스키마:
{
  "facts": string | null,
  "facts_keywords": string[],
  "legal_issue": string | null,
  "court_reasoning": string | null,
  "conclusion": string | null,
  "outcome": {
    "disposition": string,
    "direction": "원고 유리" | "피고 유리" | "일부 유리" | "unknown",
    "claim_result": string | null,
    "key_factor": string | null
  },
  "confidence": number
}

[판례 원문]
{case_full_text}
```

---

### 11.3 비교 분석 프롬프트 (고품질, Sonnet)

```
[시스템 프롬프트 — claude-sonnet, 온도 0.2]

당신은 법학 교육 전문가입니다. 두 판례의 사실관계와 판결을 비교하여
법학도가 이해할 수 있는 교육적 비교 분석을 제공합니다.

지시:
1. common_points: 두 판례에서 공통되는 사실관계 요소. 2~4개.
2. turning_points: 판결이 달라진 핵심 분기점. 최대 3개.
   각 분기점은 factor/base_value/compare_value/impact 포함.
3. conclusion_diff: 최종 결론 차이를 1~2문장으로 명확하게.
4. 법학 교재 수준의 명확한 한국어 사용. 지나친 단순화 금지.
5. 원문에 근거 없는 해석 추가 금지.

[기준 판례]
사실관계: {base_facts}
쟁점: {base_issue}
판결 이유: {base_reasoning}
결론: {base_conclusion}

[비교 판례]
사실관계: {compare_facts}
쟁점: {compare_issue}
판결 이유: {compare_reasoning}
결론: {compare_conclusion}
```

---

### 11.4 프롬프트 버전 관리 정책

- 프롬프트는 코드베이스에서 별도 `prompts/` 디렉토리로 분리 관리
- 각 프롬프트 파일에 버전 태그 명시: `# v1.2 | 2025-08-01`
- 프롬프트 변경 시 평가 세트(섹션 8) 재실행 후 결과 비교 필수
- A/B 테스트 가능하도록 프롬프트 버전을 응답 메타데이터에 포함

```json
"_meta": {
  "prompt_version": "intent_parser_v1.2",
  "model": "claude-haiku-4-5",
  "latency_ms": 430
}
```

---

## 12. 보안 & 비용 관리

### 12.1 API 보안

**인증 & 인가**

```
인증 흐름:
사용자 → JWT Access Token (15분 만료) + Refresh Token (7일, httpOnly 쿠키)
         → Next.js API Route에서 검증
         → 백엔드 서비스 내부 통신은 서비스 계정 토큰

Free / Pro 플랜 구분:
- JWT payload에 plan: "free" | "pro" 포함
- API Route 미들웨어에서 플랜별 rate limit 적용
```

**Rate Limiting**

```typescript
const RATE_LIMITS = {
  free: {
    search:   { requests: 20,  window: "1d" },
    compare:  { requests: 10,  window: "1mo" },
    ai_summary: { requests: 5, window: "1mo" },
  },
  pro: {
    search:   { requests: 1000, window: "1d" },
    compare:  { requests: 999999, window: "1mo" },  // 무제한
    ai_summary: { requests: 999999, window: "1mo" },
  }
}
```

**입력 검증**

- 자연어 쿼리 최대 500자 제한 (LLM 비용 및 인젝션 방어)
- 조문 입력 정규식 화이트리스트 검증
- API 요청 바디 JSON Schema 검증 (zod / joi)

---

### 12.2 LLM 비용 추정 및 관리

LLM 호출은 서비스 전체 비용의 가장 큰 비중을 차지한다. 미리 추정하고 상한을 설정해야 한다.

**호출 빈도 및 비용 추정 (MAU 1만 명 기준)**

| 호출 유형 | 빈도 (월) | 모델 | 평균 토큰 | 월 예상 비용 |
|----------|----------|------|----------|------------|
| 자연어 Intent 파싱 | 50,000회 | Haiku | ~400 tokens | ~$6 |
| 판례 카드 요약 (캐시 히트 50%) | 30,000회 | Haiku | ~800 tokens | ~$12 |
| 비교 분석 생성 | 15,000회 | Sonnet | ~3,000 tokens | ~$135 |
| 판례 구조화 배치 (신규 판례) | 월 5,000건 | Haiku | ~2,000 tokens | ~$5 |
| **합계** | | | | **~$160/월** |

> MAU 1만 기준 월 ~16만 원 수준. Pro 구독 수익으로 커버 가능.

**비용 제어 전략**

```python
# 1. 판례 카드 요약은 Redis 캐시 (TTL 30일)
# 키: f"summary:{case_id}:{prompt_version}"
cache_key = f"summary:{case_id}:v1.2"
cached = await redis.get(cache_key)
if cached:
    return cached

# 2. 비교 분석은 판례 쌍 단위 캐시 (순서 무관)
pair_key = "_".join(sorted([base_id, compare_id]))
cache_key = f"compare:{pair_key}:v1.2"

# 3. 배치 구조화는 야간 오프피크에 실행
# 4. 월별 LLM 비용 알림 ($200 초과 시 Slack 알림)
```

---

### 12.3 판례 원문 저작권 처리

| 소스 | 저작권 상태 | CaseLens 처리 방식 |
|------|-----------|-----------------|
| 국가법령정보 API 제공 판례 | 공공저작물 자유이용 | 원문 저장 및 표시 가능 |
| 헌재 Open API 제공 결정문 | 공공저작물 자유이용 | 원문 저장 및 표시 가능 |
| 대법원 glaw 크롤링 | 이용 조건 확인 필요 | 법률 자문 후 결정 |
| LBox, 케이스노트 등 민간 DB | 유료 라이선스 | 파트너십 계약 필요 |

- 서비스 내 판례 원문 표시 시 출처(법원명, 사건번호, 선고일) 명시 의무화
- AI 요약/비교 분석은 2차 저작물이므로 별도 저작권 검토 필요

---

## 13. 배포 & 인프라 구성

### 13.1 전체 인프라 구성도

```
                        [사용자]
                           │
                     CloudFront CDN
                           │
              ┌────────────┴────────────┐
              │       ALB (HTTPS)        │
              └────────────┬────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
  │  Next.js     │ │  검색 API    │ │  수집 워커   │
  │  (ECS)       │ │  (FastAPI,   │ │  (ECS,       │
  │  (UI + BFF)  │ │   ECS)       │ │   스케줄)    │
  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
         │                │                │
         └────────────────┼────────────────┘
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
  ┌──────────┐    ┌──────────────┐   ┌──────────────┐
  │PostgreSQL│    │  Redis       │   │임베딩 서버   │
  │ (RDS)    │    │ (ElastiCache)│   │(EC2, GPU     │
  │          │    │              │   │ 또는 API)    │
  └──────────┘    └──────────────┘   └──────────────┘
```

---

### 13.2 환경 분리

| 환경 | 용도 | 특이사항 |
|------|------|---------|
| `local` | 개발자 로컬 | Docker Compose로 PostgreSQL + Redis 구동 |
| `staging` | QA / 기능 검증 | 프로덕션과 동일 아키텍처, 판례 DB 10% 샘플 |
| `production` | 실 서비스 | Multi-AZ RDS, CloudFront 캐싱 |

**환경 변수 관리**

```bash
# .env.local (로컬만, git 제외)
ANTHROPIC_API_KEY=sk-ant-...
DB_URL=postgresql://...
REDIS_URL=redis://...
LAW_API_KEY=...
EMBEDDING_MODEL_URL=http://localhost:8001

# 프로덕션: AWS Secrets Manager + ECS Task Definition 환경변수 주입
```

---

### 13.3 CI/CD 파이프라인

```
GitHub Push (main 브랜치)
       │
       ▼
GitHub Actions
  ├─ 1. 타입 체크 (tsc --noEmit)
  ├─ 2. 린트 (ESLint)
  ├─ 3. 단위 테스트 (Jest)
  ├─ 4. 검색 품질 평가 (평가 세트 자동 실행, 임계 미달 시 배포 중단)
  └─ 5. Docker 빌드 & ECR 푸시
       │
       ▼
ECS Rolling Update (무중단 배포)
  - 헬스체크 통과 후 구버전 태스크 교체
  - 실패 시 자동 롤백
```

**검색 품질 게이트 (4단계)**

```python
# CI에서 자동 실행되는 품질 검사
# 아래 기준 미달 시 배포 차단
QUALITY_GATES = {
    "statute_search_precision_at_10": 0.75,   # 기준: 0.80 → 여유 마진 적용
    "natural_search_recall_at_5": 0.55,
    "compare_candidate_quality": 0.60,
}
```

---

### 13.4 모니터링 & 알림

**수집 지표**

```
Application:
  - 검색 API latency (p50, p95, p99)
  - LLM 응답 시간 및 에러율
  - 캐시 히트율 (Redis)
  - 사용자 피드백 not_relevant 비율

Infrastructure:
  - ECS CPU/메모리 사용률
  - RDS 연결 수, 쿼리 응답 시간
  - pgvector 인덱스 크기
  - Elasticsearch 클러스터 상태

Business:
  - 일별 검색 수 / 비교 수
  - Free → Pro 전환 수
  - LLM 비용 ($)
```

**알림 임계**

| 지표 | 경고 | 긴급 |
|------|------|------|
| 검색 API p95 latency | 3초 | 6초 |
| LLM 에러율 | 3% | 10% |
| not_relevant 피드백 비율 | 20% | 35% |
| 월 LLM 비용 | $200 | $350 |
| RDS CPU | 70% | 90% |

---

## 14. 구현 의사결정 및 전체 구축 프로세스

이 문서는 신규 구축을 전제로 하되, 구현팀이 다시 아키텍처 결정을 반복하지 않도록 MVP 기준의 기본 결정을 명시한다.

### 14.1 확정 아키텍처

| 영역 | MVP 결정 | 확장 단계 |
|------|----------|-----------|
| Frontend | Next.js + TypeScript | 동일 유지 |
| BFF | Next.js API Routes | 인증/요금제/사용량 제어 담당 |
| Search API | FastAPI | 검색, 임베딩, 판례 비교, 파이프라인 연동 담당 |
| DB | PostgreSQL 16 + pgvector | 대규모 시 Qdrant 분리 검토 |
| 전문 검색 | MVP에서는 PostgreSQL full-text 또는 단순 BM25 대체 | Phase 4에서 Elasticsearch 도입 |
| Cache | MVP에서는 DB/메모리 캐시 최소 사용 | Redis 도입 |
| LLM | Claude Haiku/Sonnet 기준 | 비용/성능에 따라 provider adapter 구조화 |
| Pipeline | Python CLI + cron | Airflow 또는 managed workflow 도입 |
| Infra | Docker Compose local, AWS ECS/RDS production | 규모 증가 시 서비스 분리 |

**결정 이유:** 판례 수집, 구조화, 임베딩, 검색 실험은 Python 생태계가 유리하므로 Search API와 pipeline은 FastAPI/Python으로 분리한다. Next.js는 UI, 인증, 결제, 사용량 제한, BFF에 집중한다.

### 14.2 MVP와 확장 라벨

문서에서 사용하는 기술은 다음 기준으로 구분한다.

```text
[MVP] 반드시 초기 구현에 포함
[Phase 2] 비교 품질 개선 후 포함
[Phase 3] 운영/평가 안정화 후 포함
[Scale] 데이터/트래픽 증가 시 포함
```

예시:

- [MVP] PostgreSQL + pgvector
- [MVP] 규칙 기반 조문 파서 + 법령 API 검증
- [MVP] 자연어 intent parser
- [MVP] 기준 판례 선택 및 비교 뷰
- [Phase 2] outcome_contrast_score 정교화
- [Phase 3] 평가 세트 기반 CI 품질 게이트
- [Scale] Elasticsearch, Redis, Qdrant, Airflow

### 14.3 전체 구축 프로세스

```text
1. 요구사항 확정
   - 대상 사용자, MVP 도메인, 데이터 범위, 면책 문구 확정

2. 데이터 소스 검증
   - law.go.kr API 키 발급
   - 샘플 판례 100건 수집
   - 원문 HTML/본문 품질 확인

3. DB 스키마 구축
   - cases, case_paragraphs, case_structures, case_embeddings 생성
   - articles, law_aliases, search_queries, feedbacks 생성
   - pgvector extension 및 인덱스 적용

4. 수집 파이프라인 구현
   - 조문/키워드별 판례 목록 수집
   - 판례 상세 원문 저장
   - 중복 제거 및 source hash 저장

5. 원문 정규화
   - HTML 제거
   - 문단 분리
   - 주문/이유/판시사항/참조조문 섹션 추출
   - paragraph_id 부여

6. 구조화
   - 규칙 기반 1차 구조화
   - 누락/저신뢰 판례만 LLM 구조화
   - evidence_spans 연결
   - confidence_score 계산

7. 임베딩 생성
   - facts, issue, holding, distinction, combined 텍스트 생성
   - 모델 버전과 차원 저장
   - pgvector 저장 및 인덱스 생성

8. 검색 API 구현
   - 조문 검색
   - 자연어 검색
   - 사건번호/판례 ID 검색
   - RRF 또는 weighted score 병합

9. 비교 API 구현
   - 기준 판례 기반 후보 검색
   - outcome/facet 대비도 계산
   - LLM 비교 요약 생성
   - 원문 근거 링크 반환

10. 프론트엔드 구현
    - 검색 입력
    - 기준 판례 선택
    - 그룹별 결과 카드
    - 나란히 비교 뷰
    - 원문 근거 확인 UI
    - 피드백 제출 UI

11. 품질 평가
    - 조문/자연어/비교 평가 세트 생성
    - Top-k 지표 측정
    - LLM 구조화 정확도 표본 검수

12. 보안/비용 제어
    - 인증, rate limit, plan limit
    - LLM 캐시
    - 월 비용 알림
    - 입력 길이 제한 및 prompt injection 방어

13. 배포
    - staging 환경 구성
    - 데이터 10% 샘플로 QA
    - production RDS/ECS 배포
    - 헬스체크/롤백 설정

14. 운영
    - 신규 판례 증분 수집
    - needs_review 큐 처리
    - 검색 품질 대시보드 모니터링
    - 피드백 기반 랭킹 가중치 조정
```

### 14.4 Definition of Done

| 단계 | 완료 기준 |
|------|-----------|
| 데이터 수집 | MVP 도메인별 최소 500건 이상 수집, 중복률 3% 이하 |
| 구조화 | 핵심 필드 confidence 0.7 이상 판례 70% 이상 |
| 검색 | 조문 검색 precision@10 0.8 이상 |
| 자연어 | 관련 판례 Top-5 평균 3건 이상 |
| 비교 | 유효 비교 후보 Top-5 평균 2건 이상 |
| UI | 기준 판례 선택부터 비교 결과 확인까지 3클릭 이내 |
| 운영 | p95 검색 응답 2.5초 이하, LLM 오류율 3% 이하 |

---

## 15. DB 물리 스키마 및 인덱스 설계

### 15.1 핵심 테이블

```sql
CREATE TABLE cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id TEXT,
  case_no TEXT NOT NULL,
  court_name TEXT,
  court_level TEXT,
  decision_date DATE,
  case_name TEXT,
  case_type TEXT,
  source TEXT NOT NULL,
  source_url TEXT,
  raw_text TEXT NOT NULL,
  raw_html TEXT,
  source_hash TEXT NOT NULL,
  collected_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (case_no, decision_date, court_name)
);

CREATE TABLE case_paragraphs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  paragraph_id TEXT NOT NULL,
  section_type TEXT,
  paragraph_order INT NOT NULL,
  text TEXT NOT NULL,
  char_start INT,
  char_end INT,
  UNIQUE (case_id, paragraph_id)
);

CREATE TABLE case_structures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  cited_articles TEXT[] DEFAULT '{}',
  referenced_cases TEXT[] DEFAULT '{}',
  facts TEXT,
  facts_keywords TEXT[] DEFAULT '{}',
  legal_issue TEXT,
  court_reasoning TEXT,
  conclusion TEXT,
  outcome JSONB NOT NULL DEFAULT '{}',
  facets JSONB NOT NULL DEFAULT '{}',
  evidence_spans JSONB NOT NULL DEFAULT '{}',
  confidence_score NUMERIC(4,3) DEFAULT 0,
  review_status TEXT DEFAULT 'unreviewed',
  is_reviewed BOOLEAN DEFAULT false,
  prompt_version TEXT,
  model_name TEXT,
  processed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE case_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  embedding_type TEXT NOT NULL,
  embedding_model TEXT NOT NULL,
  embedding_dimension INT NOT NULL,
  content_text TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  embedding vector(768) NOT NULL,
  needs_regeneration BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (case_id, embedding_type, embedding_model, content_hash)
);
```

### 15.2 법령 및 검색 운영 테이블

```sql
CREATE TABLE laws (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  law_code TEXT UNIQUE,
  official_name TEXT NOT NULL,
  short_name TEXT,
  effective_date DATE,
  source_url TEXT
);

CREATE TABLE law_aliases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  law_id UUID NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
  alias TEXT NOT NULL,
  UNIQUE (law_id, alias)
);

CREATE TABLE articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  law_id UUID NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
  article_code TEXT NOT NULL,
  article_no TEXT NOT NULL,
  paragraph_no TEXT,
  subparagraph_no TEXT,
  title TEXT,
  body TEXT,
  normalized_ref TEXT NOT NULL,
  effective_date DATE,
  UNIQUE (law_id, article_code, paragraph_no, subparagraph_no)
);

CREATE TABLE search_queries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  query_text TEXT NOT NULL,
  query_type TEXT NOT NULL,
  parsed_query JSONB,
  result_count INT,
  latency_ms INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE comparison_feedbacks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  base_case_id UUID REFERENCES cases(id),
  compare_case_id UUID REFERENCES cases(id),
  query_id UUID REFERENCES search_queries(id),
  label TEXT NOT NULL,
  reason TEXT,
  comment TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE llm_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  purpose TEXT NOT NULL,
  model_name TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  output JSONB,
  latency_ms INT,
  token_input INT,
  token_output INT,
  cost_usd NUMERIC(10,6),
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### 15.3 인덱스

```sql
CREATE INDEX idx_cases_case_no ON cases(case_no);
CREATE INDEX idx_cases_decision_date ON cases(decision_date DESC);
CREATE INDEX idx_cases_court_level ON cases(court_level);
CREATE INDEX idx_case_structures_articles ON case_structures USING gin(cited_articles);
CREATE INDEX idx_case_structures_outcome ON case_structures USING gin(outcome);
CREATE INDEX idx_case_structures_facets ON case_structures USING gin(facets);
CREATE INDEX idx_case_paragraphs_case_order ON case_paragraphs(case_id, paragraph_order);
CREATE INDEX idx_articles_normalized_ref ON articles(normalized_ref);

CREATE INDEX idx_case_embeddings_vector
ON case_embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

> 임베딩 모델을 1024차원으로 변경할 경우 `case_embeddings_1024` 테이블을 별도로 만들거나, vector dimension별 테이블을 분리한다. pgvector는 컬럼 차원이 고정되므로 혼용 금지.

---

## 16. 법령/조문 정규화 정책

### 16.1 입력 허용 예시

```text
민법 제750조
민법 750조
민법 제750조 제1항
민법 제750조의2
민법 750
민 제750조
자동차손해배상보장법 제3조
자배법 제3조
근로기준법 제36조
근기법 36조
주택임대차보호법 제3조의2 제2항
```

### 16.2 정규화 결과

```json
{
  "raw": "자배법 제3조",
  "law_alias": "자배법",
  "law_official_name": "자동차손해배상 보장법",
  "article_no": "3",
  "article_branch_no": null,
  "paragraph_no": null,
  "subparagraph_no": null,
  "normalized_ref": "자동차손해배상보장법_제3조",
  "confidence": 0.94
}
```

### 16.3 정규화 절차

```python
def normalize_article_ref(raw: str) -> NormalizedArticle:
    text = normalize_whitespace(raw)
    text = normalize_korean_number_spacing(text)
    law_alias, rest = split_law_name_and_article(text)
    law = resolve_law_alias(law_alias)
    article = parse_article_number(rest)
    validate_article_exists(law, article)
    return build_normalized_ref(law, article)
```

### 16.4 모호성 처리

| 상황 | 처리 |
|------|------|
| 법령 약칭이 여러 법령에 매칭 | 후보 목록 반환 후 사용자 선택 |
| 조문 번호는 있으나 법령명 없음 | 자연어 키워드와 함께 LLM intent로 후보 추정, confidence 낮게 설정 |
| 존재하지 않는 조문 | `ARTICLE_NOT_FOUND` 반환 |
| 개정 전/후 조문 차이 | 판례 선고일 기준 시행 법령 우선 매칭 |
| `제750조의2` 같은 가지번호 | `article_no=750`, `article_branch_no=2`로 분리 저장 |

---

## 17. 검색 실패 및 예외 UX

검색 실패는 단순 에러가 아니라 사용자가 다음 행동을 할 수 있게 설계한다.

### 17.1 결과 없음 처리

| 상황 | 사용자 메시지 | 시스템 행동 |
|------|---------------|-------------|
| 조문 파싱 실패 | 조문 형식을 확인해 주세요 | 유사 법령명/조문 후보 표시 |
| 존재하지 않는 조문 | 현재 법령 DB에서 확인되지 않는 조문입니다 | 공식 법령 검색 링크 제공 |
| 조문 검색 0건 | 해당 조문을 직접 인용한 판례가 없습니다 | 같은 법률의 인접 조문, 키워드 검색 제안 |
| 자연어 confidence 낮음 | 사실관계를 조금 더 알려 주세요 | 추가 질문 1개만 표시 |
| 비교 후보 부족 | 결과가 다른 유사 판례가 충분하지 않습니다 | outcome 조건 완화 결과와 이유 표시 |
| LLM 비교 timeout | AI 비교 요약 생성이 지연되고 있습니다 | 구조화 필드 기반 기본 비교 먼저 표시 |

### 17.2 Fallback 검색 정책

```python
def search_with_fallback(query):
    result = exact_search(query)
    if result.count >= 3:
        return result

    result = hybrid_search(query)
    if result.count >= 3:
        return result.with_notice("정확 일치 결과가 적어 유사 검색을 함께 사용했습니다.")

    result = relaxed_search(query)
    return result.with_notice("검색 조건을 완화한 후보입니다. 원문 확인이 필요합니다.")
```

### 17.3 비교 후보 완화 순서

```text
1. 같은 legal_domain + 같은 주요 조문 + outcome contrast
2. 같은 legal_domain + fact similarity + outcome contrast
3. 같은 legal_domain + issue similarity
4. 같은 키워드 cluster 내 대표 반례
```

각 완화 단계는 UI에 `추천 이유`로 표시한다.

---

## 18. LLM 출력 검증 및 안전장치

### 18.1 구조화 결과 검증

```python
ALLOWED_CASE_TYPES = {"민사", "형사", "행정", "헌법", "가사"}
ALLOWED_DIRECTIONS = {"원고 유리", "피고 유리", "일부 유리", "검사 유리", "피고인 유리", "unknown"}


def validate_llm_structure(output):
    errors = []
    if output.get("case_type") not in ALLOWED_CASE_TYPES:
        errors.append("invalid_case_type")

    confidence = output.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append("invalid_confidence")

    outcome = output.get("outcome") or {}
    if outcome.get("direction") not in ALLOWED_DIRECTIONS:
        errors.append("invalid_outcome_direction")

    for article in output.get("cited_articles", []):
        if not article_exists(article):
            errors.append(f"unknown_article:{article}")

    if not has_valid_evidence_spans(output):
        errors.append("missing_evidence")

    return errors
```

### 18.2 검증 실패 처리

| 오류 | 처리 |
|------|------|
| `invalid_json` | 재시도 1회, 실패 시 규칙 기반 결과 사용 |
| `unknown_article` | 해당 조문 제거, confidence 감점 |
| `missing_evidence` | 사용자 노출 제한, 검수 큐 이동 |
| `invalid_outcome_direction` | direction을 `unknown`으로 대체 |
| `low_confidence` | 검색 가중치 낮춤, UI에 검수 전 표시 |

### 18.3 Prompt Injection 방어

- 사용자 입력과 시스템 지시를 명확히 분리한다.
- 판례 원문/사용자 입력 안의 “이전 지시 무시” 같은 문구는 데이터로만 취급한다.
- LLM 출력은 JSON Schema로 검증한다.
- LLM이 반환한 URL, 법령, 금액, 판례번호는 DB/정규식으로 재검증한다.

---

## 19. 법률 서비스 고지 및 책임 범위

CaseLens는 법률 정보 탐색 및 교육용 비교 도구이며, 법률 자문 서비스가 아니다.

### 19.1 필수 고지 문구

```text
CaseLens의 검색 결과, AI 요약, 판례 비교 분석은 참고용 정보입니다.
법률적 판단이나 실제 사건 대응은 반드시 판례 원문, 최신 법령, 전문가 검토를 통해 확인해야 합니다.
본 서비스는 판례 데이터 누락, AI 요약 오류, 법령 개정 미반영 가능성을 포함합니다.
```

### 19.2 UI 표시 위치

| 위치 | 표시 방식 |
|------|-----------|
| 첫 화면 하단 | 짧은 면책 고지 |
| 결과 카드 | `AI 요약: 원문 확인 필요` 배지 |
| 비교 분석 | 분석 하단에 고지 전문 표시 |
| 원문 링크 옆 | 공식 출처 확인 버튼 |
| 회원가입/결제 | 서비스 이용약관에 법률 자문 아님 명시 |

### 19.3 법령 최신성 정책

- 법령 조문은 수집/검증 시점 기준으로 저장한다.
- 판례 선고일 당시 법령과 현재 법령이 다를 수 있음을 표시한다.
- 조문 검색 결과에는 `현행 조문 기준` 또는 `판례 당시 조문 기준` 라벨을 둔다.

---

## 20. 남은 부족 부분 및 의사결정 사항

v0.4 기준으로 주요 기술 설계는 보강되었지만, 실제 개발 착수 전 아래 항목은 추가 확정이 필요하다.

### 20.1 아직 부족한 부분

| 부족한 부분 | 왜 중요한가 | 보강 방향 |
|-------------|-------------|-----------|
| 실제 평가 데이터셋 부재 | 검색 품질 목표를 검증할 수 없음 | 조문 30개, 자연어 50개, 비교 30쌍 라벨링 |
| 초기 수집 대상 조문 목록 부재 | 수집 범위가 불명확함 | MVP 도메인별 핵심 조문 50~100개 선정 |
| 관리자 검수 UI 상세 부재 | 구조화 오류를 운영에서 고치기 어려움 | needs_review 큐, 필드 수정, 재임베딩 버튼 설계 |
| 과금/플랜 정책 상세 부재 | rate limit과 비용 정책 구현 기준 부족 | Free/Pro 가격, 월 비교 횟수, 팀 플랜 확정 |
| 개인정보 처리방침 부재 | 실제 서비스 배포 시 필수 | 수집 데이터, 사용자 검색 로그, 보존 기간 정의 |
| 원문 표시 라이선스 검토 미완료 | 법적 리스크 | law.go.kr/glaw/민간 DB별 이용 조건 법률 검토 |
| 모델/provider fallback 정책 부족 | LLM 장애 시 서비스 저하 | Anthropic 장애 시 로컬 요약/다른 provider fallback 정의 |
| 접근성/모바일 UX 기준 부족 | 학생 사용성에 영향 | WCAG 기준, 모바일 비교 화면 별도 설계 |
| 테스트 전략 상세 부족 | 구현 안정성 부족 | unit/integration/e2e/search-quality 테스트 구분 |
| 데이터 삭제/재수집 정책 부족 | 잘못 수집된 판례 처리 필요 | source_hash, pipeline_run_id, soft delete 정책 추가 |

### 20.2 최종 의사결정 체크리스트

```text
[ ] MVP 검색 API는 FastAPI 분리 구조로 확정했는가?
[ ] MVP에서는 Elasticsearch 없이 pgvector/PostgreSQL로 시작하는가?
[ ] 초기 임베딩 모델과 차원을 하나로 고정했는가?
[ ] MVP 도메인과 핵심 조문 목록을 확정했는가?
[ ] 판례 원문 표시 범위와 저작권 검토가 끝났는가?
[ ] 평가 데이터셋을 누가, 어떤 기준으로 라벨링할지 정했는가?
[ ] 관리자 검수 프로세스와 책임자가 정해졌는가?
[ ] 법률 자문 아님 고지와 이용약관 초안이 준비됐는가?
[ ] LLM 비용 상한과 장애 fallback이 정해졌는가?
[ ] production 배포 전 품질 게이트 기준을 확정했는가?
```

### 20.3 다음 문서로 분리하면 좋은 항목

현재 기술 명세서가 너무 커질 수 있으므로, 아래는 별도 문서로 분리하는 것을 권장한다.

| 문서 | 내용 |
|------|------|
| `DataCollectionPlan.md` | 수집 대상 조문, 수집 우선순위, API 호출 정책 |
| `EvaluationSet.md` | 평가 쿼리, 정답 판례, 라벨링 기준 |
| `AdminReviewSpec.md` | 구조화 검수 UI, 권한, 수정 이력 |
| `PromptRegistry.md` | 프롬프트 버전, 평가 결과, 변경 이력 |
| `LegalPolicy.md` | 저작권, 개인정보, 면책 고지, 이용약관 초안 |
| `TestStrategy.md` | 단위/통합/E2E/검색품질 테스트 계획 |

---



### ✅ 잘 설계된 부분

- **규칙 기반 + LLM 상호보완 구조** — 비용 효율적이고 실용적. 판례 원문의 비정형성을 현실적으로 인정한 좋은 접근.
- **조문/자연어 이중 입력 경로** — 사용자 진입 방식을 다양화하여 학습 목적에 맞게 유연.
- **"유사 사실관계 + 상이한 결과"라는 비교 기준** — 법학 교육에서 가장 중요한 비교 방식. 핵심을 정확히 짚음.

---

### ⚠️ 논리적 이슈 & 개선 제안

#### 이슈 1: "결과가 다른 판례"의 정의가 불명확

**현재 설계의 문제:**  
판례 결과(outcome)를 `인용/기각/파기환송` 등으로 단순 분류하면, **법적으로 의미 있는 차이**를 놓칠 수 있음.

예) 두 판례 모두 "파기환송"이지만 — 하나는 손해배상액 증액, 다른 하나는 감액을 위한 파기환송일 수 있음.

**개선 제안:**
```json
"outcome": {
  "disposition": "파기환송",          // 기존 분류
  "direction": "원고 유리",           // 방향성 추가 (LLM이 판단)
  "key_factor": "과실 비율 재산정"     // 결론의 핵심 근거
}
```
→ 유사도 검색 시 `disposition`이 아닌 `direction` 기준으로 필터링하는 것이 더 교육적으로 유용.

---

#### 이슈 2: 벡터 유사도만으로는 "사실관계 유사"를 보장하기 어려움

**현재 설계의 문제:**  
`facts_vector` 코사인 유사도가 높아도 법적으로는 완전히 다른 사건일 수 있음.

예) "교통사고로 사람이 다쳤다"는 표현이 있는 모든 판례가 유사하게 매칭될 위험.

**개선 제안 — Structured Facets 필터 추가:**
```python
FACET_FIELDS = [
    "legal_domain",     # 손해배상 / 계약 / 형사책임 ...
    "key_parties",      # 개인 vs 개인 / 개인 vs 기업 / 행정처분 ...
    "harm_type",        # 신체 / 재산 / 명예 ...
    "causal_relation",  # 직접 / 간접
]
# 벡터 유사도 검색 전, facet 필터로 후보군을 먼저 좁혀서
# 검색 공간 축소 + 매칭 정밀도 향상
```

---

#### 이슈 3: 자연어 입력의 LLM 파싱 결과 신뢰성

**현재 설계의 문제:**  
LLM이 `inferred_articles`(관련 법조문)를 추정할 때, 존재하지 않는 조문을 생성(hallucination)할 수 있음.

**개선 제안:**
```python
def validate_inferred_articles(articles: list[str]) -> list[str]:
    """LLM이 추정한 조문을 법령 DB에서 실존 여부 검증 후 사용"""
    return [a for a in articles if law_db.exists(a)]

# inferred_articles는 검색 가중치를 낮게 설정 (보조 신호로만 사용)
QUERY_WEIGHTS = {
    "keywords":          0.40,   # 높음 — 명확한 사용자 의도
    "facts_vector":      0.35,   # 높음 — 의미 유사도
    "inferred_articles": 0.15,   # 낮음 — 검증 안된 LLM 추정
    "case_type":         0.10,   # 메타 필터
}
```

---

#### 이슈 4: 판례 수집의 completeness 문제

**현재 설계의 문제:**  
법령 API는 대법원 판례 중심이고, 하급심 판례 상당수는 공개되지 않음.  
특히 **지방법원 1심 판례** 부재 시, "사실관계 유사 + 결과 상이" 판례를 찾기 위한 모수가 줄어듦.

**개선 제안:**
- MVP 범위를 "대법원 + 고등법원 판례"로 명시적으로 한정하고, 사용자에게 데이터 범위 고지
- 차후 판례 크라우드소싱(변호사 파트너십) 또는 LBox, 케이스노트 등 판례 DB 파트너십 검토

---

#### 이슈 5: 임베딩 벡터의 차원 통일 필요

**현재 설계의 문제:**  
`ko-sbert`(768차원)와 `bge-m3`(1024차원)를 혼용 시, 가중 유사도 계산에서 차원 불일치 발생.

**개선 제안:**
- 단일 임베딩 모델로 통일 (초기: `ko-sbert-multitask-klue-roberta-base`, 768차원 권장)
- 모델 교체 시 전체 판례 재임베딩 배치 작업 스케줄링 고려

---

### 💡 추가 권장 개선사항

#### 개선 A: 비교 앵커 포인트 (Comparison Anchor) 명시

단순히 두 판례를 나란히 놓는 것보다, **"무엇이 갈림길이었는가"**를 명시하면 교육 효과 극대화.

```
기준 판례         비교 판례
─────────         ─────────
[공통]  교통사고, 신체 상해, 과실 여부 다툼
        ────────────────── 분기점 ──────────────────
[차이]  피해자 동승 여부    없음          있음 → 과실상계 적용
[차이]  보험 가입 여부      무보험        유보험 → 직접 청구권
[결과]                      전부 인용     일부 기각 (30% 과실상계)
```

→ LLM에게 "두 판례의 분기점(turning point)을 최대 3개 추출"하도록 프롬프트 설계

---

#### 개선 B: 판례 클러스터링 사전 구축

매 요청마다 실시간으로 유사 판례를 찾으면 지연 발생.  
오프라인으로 **유사 판례 클러스터를 미리 구축**하여 응답 속도 개선.

```python
# 배치 작업: 주 1회
# K-means 또는 HDBSCAN으로 판례 클러스터링
# 각 클러스터에 "대표 판례"와 "반례 판례" 쌍을 미리 매핑
# → 사용자 요청 시 실시간 검색 대신 클러스터 조회
```

---

#### 개선 C: 피드백 루프 구축

사용자가 "이 비교는 관련 없다"고 표시하면 → 유사도 모델 재학습 데이터로 활용  
→ 서비스 운영이 곧 데이터 수집이 되는 선순환 구조

---

*본 문서는 CaseLens 내부 기술 참고용이며, 구현 중 변경될 수 있습니다.*


