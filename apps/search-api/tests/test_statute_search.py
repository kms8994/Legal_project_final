from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.api.search import get_statute_search_service
from app.core.config import settings
from app.main import app
from app.repositories.statute_search import ArticleRecord, CaseSearchRow, SearchEvidenceRecord
from app.services.statute_search import StatuteSearchService


class FakeStatuteRepository:
    def resolve_article(self, law_name: str, article_no: int) -> ArticleRecord | None:
        if law_name == "민법" and article_no == 750:
            return ArticleRecord(
                normalized_ref="민법_제750조",
                law_name="민법",
                article_no=750,
            )
        return None

    def count_cases_for_article(self, normalized_ref: str) -> int:
        assert normalized_ref == "민법_제750조"
        return 1

    def search_cases_for_article(
        self,
        normalized_ref: str,
        *,
        page: int,
        size: int,
        sort: str,
    ) -> list[CaseSearchRow]:
        assert normalized_ref == "민법_제750조"
        assert page == 1
        assert size == 20
        assert sort == "relevance"
        return [
            CaseSearchRow(
                case_id="11111111-1111-1111-1111-111111111111",
                case_no="2021다12345",
                court_name="대법원",
                court_level="supreme",
                decision_date=date(2022, 3, 15),
                case_name="손해배상",
                case_type="민사",
                legal_domain="손해배상",
                source_url="https://www.law.go.kr/precInfoP.do?precSeq=000000",
                cited_articles=["민법_제750조"],
                facts="전방주시 의무 위반이 문제된 사안입니다.",
                conclusion="원고의 청구를 일부 인용했습니다.",
                outcome={"disposition": "일부 인용", "direction": "원고 일부 유리"},
                facets={
                    "primary_domain": "damages",
                    "secondary_domains": [],
                    "issue_tags": ["negligence"],
                    "mvp_relevance": "mvp_relevant",
                },
                evidence_spans={"facts": [{"paragraph_id": "P001"}], "reasoning": ["p18"]},
                review_status="pending",
                confidence_score=0.82,
            )
        ]

    def list_cases_for_natural_search(self) -> list[CaseSearchRow]:
        return [
            CaseSearchRow(
                case_id="11111111-1111-1111-1111-111111111111",
                case_no="2021??2345",
                court_name="?踰뺤썝",
                court_level="supreme",
                decision_date=date(2022, 3, 15),
                case_name="Traffic damages",
                case_type="civil",
                legal_domain="damages",
                source_url="https://www.law.go.kr/precInfoP.do?precSeq=000000",
                cited_articles=["민법_제750조"],
                facts="traffic accident victim negligence damages",
                conclusion="The claim was partially accepted.",
                outcome={"disposition": "partially accepted", "key_factor": "negligence"},
                facets={
                    "primary_domain": "damages",
                    "secondary_domains": [],
                    "issue_tags": ["negligence"],
                    "mvp_relevance": "mvp_relevant",
                },
                evidence_spans={"facts": ["p12"], "reasoning": ["p18"]},
                review_status="pending",
                confidence_score=0.82,
            ),
            CaseSearchRow(
                case_id="22222222-2222-2222-2222-222222222222",
                case_no="2020??1111",
                court_name="District Court",
                court_level="district",
                decision_date=date(2020, 1, 1),
                case_name="Contract",
                case_type="civil",
                legal_domain="contract",
                source_url=None,
                cited_articles=[],
                facts="contract payment dispute",
                conclusion="The claim was dismissed.",
                outcome={"disposition": "dismissed"},
                facets={
                    "primary_domain": "contract",
                    "secondary_domains": [],
                    "issue_tags": [],
                    "mvp_relevance": "out_of_scope",
                },
                evidence_spans={"facts": ["p01"]},
                review_status="pending",
                confidence_score=0.7,
            ),
            CaseSearchRow(
                case_id="33333333-3333-3333-3333-333333333333",
                case_no="2021??2222",
                court_name="District Court",
                court_level="district",
                decision_date=date(2021, 2, 2),
                case_name="Damages with contract issue",
                case_type="civil",
                legal_domain="damages",
                source_url=None,
                cited_articles=[],
                facts="contract payment dispute with incidental damages",
                conclusion="The claim was partially accepted.",
                outcome={"disposition": "partially accepted"},
                facets={
                    "primary_domain": "damages",
                    "secondary_domains": ["contract"],
                    "issue_tags": [],
                    "mvp_relevance": "mvp_relevant",
                },
                evidence_spans={"facts": ["p02"]},
                review_status="pending",
                confidence_score=0.82,
            ),
        ]

    def embedding_scores_for_query(self, query_embedding: str, embedding_model: str) -> dict[str, float]:
        assert query_embedding.startswith("[")
        assert embedding_model == "local-hash-embedding-v1"
        return {
            "11111111-1111-1111-1111-111111111111": 0.9,
            "22222222-2222-2222-2222-222222222222": 0.1,
            "33333333-3333-3333-3333-333333333333": 0.9,
        }

    def evidence_snippets_for_cases(
        self,
        case_ids: list[str],
        evidence_ids_by_case: dict[str, list[str]],
    ) -> dict[str, list[SearchEvidenceRecord]]:
        snippets = {
            "11111111-1111-1111-1111-111111111111": [
                SearchEvidenceRecord(
                    case_id="11111111-1111-1111-1111-111111111111",
                    evidence_id="P0001",
                    section_type="facts",
                    paragraph_order=12,
                    text="Driver negligence evidence paragraph.",
                ),
                SearchEvidenceRecord(
                    case_id="11111111-1111-1111-1111-111111111111",
                    evidence_id="p12",
                    section_type="facts",
                    paragraph_order=12,
                    text="Driver negligence evidence paragraph.",
                ),
                SearchEvidenceRecord(
                    case_id="11111111-1111-1111-1111-111111111111",
                    evidence_id="p18",
                    section_type="reasoning",
                    paragraph_order=18,
                    text="Court reasoning evidence paragraph.",
                ),
            ],
            "22222222-2222-2222-2222-222222222222": [
                SearchEvidenceRecord(
                    case_id="22222222-2222-2222-2222-222222222222",
                    evidence_id="p01",
                    section_type="facts",
                    paragraph_order=1,
                    text="Contract evidence paragraph.",
                ),
            ],
            "33333333-3333-3333-3333-333333333333": [
                SearchEvidenceRecord(
                    case_id="33333333-3333-3333-3333-333333333333",
                    evidence_id="p02",
                    section_type="facts",
                    paragraph_order=2,
                    text="Secondary contract evidence paragraph.",
                ),
            ],
        }
        return {
            case_id: [
                snippet
                for snippet in snippets.get(case_id, [])
                if snippet.evidence_id in set(evidence_ids_by_case.get(case_id, []))
            ]
            for case_id in case_ids
        }


def override_statute_search_service() -> StatuteSearchService:
    return StatuteSearchService(FakeStatuteRepository())


def test_search_statute_returns_contract_shape() -> None:
    app.dependency_overrides[get_statute_search_service] = override_statute_search_service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/search/statute",
            json={"query": "민법 제750조", "page": 1, "size": 20, "sort": "relevance"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["query"]["normalized_ref"] == "민법_제750조"
    assert body["query"]["article_validated"] is True
    assert body["pagination"]["total"] == 1
    assert body["results"][0]["case_no"] == "2021다12345"
    assert body["results"][0]["primary_domain"] == "damages"
    assert body["results"][0]["mvp_relevance"] == "mvp_relevant"
    assert body["results"][0]["evidence_ids"] == ["P0001", "p18"]
    assert body["results"][0]["evidence_snippets"][0]["evidence_id"] == "P0001"
    assert body["results"][0]["evidence_snippets"][0]["text"] == "Driver negligence evidence paragraph."


def test_search_statute_accepts_short_article_query() -> None:
    app.dependency_overrides[get_statute_search_service] = override_statute_search_service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/search/statute",
            json={"query": "민법 750", "page": 1, "size": 20, "sort": "relevance"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["query"]["normalized_ref"] == "민법_제750조"
    assert body["results"][0]["case_no"] == "2021다12345"


def test_search_statute_returns_404_for_unknown_internal_article() -> None:
    app.dependency_overrides[get_statute_search_service] = override_statute_search_service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/search/statute",
            json={"query": "민법 제999조"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ARTICLE_NOT_FOUND"


def test_search_natural_returns_parsed_intent_and_ranked_results() -> None:
    settings.embedding_provider = "local"
    settings.embedding_model = "local-hash-embedding-v1"
    app.dependency_overrides[get_statute_search_service] = override_statute_search_service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/search/natural",
            json={"query": "traffic accident victim negligence damages", "page": 1, "size": 10},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["search_method"] == "structured_fallback"
    assert body["parsed_intent"]["legal_domain"] == "damages"
    assert body["parsed_intent"]["confidence"] > 0.5
    assert body["pagination"]["total"] == 3
    assert body["results"][0]["case_no"] == "2021??2345"
    assert body["results"][0]["evidence_ids"] == ["p12", "p18"]
    assert body["results"][0]["evidence_snippets"][1]["evidence_id"] == "p18"


def test_search_natural_uses_general_domain_intent() -> None:
    settings.embedding_provider = "local"
    settings.embedding_model = "local-hash-embedding-v1"
    app.dependency_overrides[get_statute_search_service] = override_statute_search_service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/search/natural",
            json={"query": "contract payment dispute", "page": 1, "size": 10},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["parsed_intent"]["legal_domain"] == "contract"
    assert body["results"][0]["primary_domain"] == "contract"
    assert body["results"][1]["primary_domain"] == "damages"
    assert "contract" in body["results"][1]["secondary_domains"]
