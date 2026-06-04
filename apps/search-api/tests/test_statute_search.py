from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.api.search import get_statute_search_service
from app.main import app
from app.repositories.statute_search import ArticleRecord, CaseSearchRow
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
                evidence_spans={"facts": ["p12"], "reasoning": ["p18"]},
                review_status="pending",
                confidence_score=0.82,
            )
        ]


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
    assert body["results"][0]["evidence_ids"] == ["p12", "p18"]


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
