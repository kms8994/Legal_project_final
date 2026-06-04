from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.api.cases import get_case_detail_service
from app.api.compare import get_compare_service
from app.core.config import settings
from app.main import app
from app.repositories.cases import (
    CaseMetaRecord,
    CaseParagraphRecord,
    CaseStructureRecord,
    CompareCandidateRecord,
)
from app.services.cases import CaseDetailService


CASE_ID = "11111111-1111-1111-1111-111111111111"
COMPARE_CASE_ID = "33333333-3333-3333-3333-333333333333"


class FakeCaseDetailRepository:
    def get_case(self, case_id: str) -> CaseMetaRecord | None:
        records = {
            CASE_ID: CaseMetaRecord(
                case_id=CASE_ID,
                external_id="000000",
                case_no="2021Da2345",
                court_name="Supreme Court",
                court_level="supreme",
                decision_date=date(2022, 3, 15),
                case_name="Damages",
                case_type="civil",
                legal_domain="damages",
                source_url="https://www.law.go.kr/precInfoP.do?precSeq=000000",
                collected_at=datetime(2026, 6, 3, 16, 41, tzinfo=timezone.utc),
            ),
            COMPARE_CASE_ID: CaseMetaRecord(
                case_id=COMPARE_CASE_ID,
                external_id="000001",
                case_no="2020Da4321",
                court_name="Supreme Court",
                court_level="supreme",
                decision_date=date(2021, 11, 10),
                case_name="Similar damages",
                case_type="civil",
                legal_domain="damages",
                source_url="https://www.law.go.kr/precInfoP.do?precSeq=000001",
                collected_at=datetime(2026, 6, 3, 16, 42, tzinfo=timezone.utc),
            ),
        }
        return records.get(case_id)

    def get_structure(self, case_id: str) -> CaseStructureRecord | None:
        records = {
            CASE_ID: CaseStructureRecord(
                facts="Driver negligence was disputed.",
                legal_issue="Liability and causation",
                court_reasoning="The court considered both negligence and causation.",
                conclusion="The claim was partially accepted.",
                material_facts={"negligence_offset_issue": True, "victim_fault": False},
                outcome={"disposition": "partially accepted", "key_factor": "negligence"},
                cited_articles=["civil_act_750"],
                facets={"legal_domain": "damages"},
                evidence_spans={"facts": ["p12"], "outcome": ["p18"]},
                confidence_score=0.82,
                review_status="pending",
            ),
            COMPARE_CASE_ID: CaseStructureRecord(
                facts="Driver negligence was disputed in a similar accident.",
                legal_issue="Liability and causation",
                court_reasoning="The court emphasized victim fault.",
                conclusion="The damages amount was reduced.",
                material_facts={"negligence_offset_issue": True, "victim_fault": True},
                outcome={"disposition": "partially accepted", "key_factor": "victim fault"},
                cited_articles=["civil_act_750"],
                facets={"legal_domain": "damages"},
                evidence_spans={"facts": ["p08"], "reasoning": ["p17"]},
                confidence_score=0.84,
                review_status="pending",
            ),
        }
        return records.get(case_id)

    def list_paragraphs(self, case_id: str) -> list[CaseParagraphRecord]:
        records = {
            CASE_ID: [
                CaseParagraphRecord(
                    paragraph_id="p12",
                    section_type="facts",
                    paragraph_order=12,
                    text="Base evidence paragraph text.",
                    char_start=1200,
                    char_end=1450,
                ),
                CaseParagraphRecord(
                    paragraph_id="p18",
                    section_type="order",
                    paragraph_order=18,
                    text="Base outcome paragraph text.",
                    char_start=1500,
                    char_end=1600,
                ),
            ],
            COMPARE_CASE_ID: [
                CaseParagraphRecord(
                    paragraph_id="p08",
                    section_type="facts",
                    paragraph_order=8,
                    text="Compare evidence paragraph text.",
                    char_start=800,
                    char_end=900,
                ),
                CaseParagraphRecord(
                    paragraph_id="p17",
                    section_type="reasoning",
                    paragraph_order=17,
                    text="Compare reasoning paragraph text.",
                    char_start=1700,
                    char_end=1800,
                ),
            ],
        }
        return records.get(case_id, [])

    def list_compare_candidates(self, case_id: str) -> list[CompareCandidateRecord]:
        if case_id != CASE_ID:
            return []
        return [
            CompareCandidateRecord(
                case_id="33333333-3333-3333-3333-333333333333",
                case_no="2020Da4321",
                court_name="Supreme Court",
                decision_date=date(2021, 11, 10),
                case_name="Similar damages",
                legal_domain="damages",
                facts="Driver negligence was disputed in a similar accident.",
                legal_issue="Liability and causation",
                conclusion="The damages amount was reduced.",
                material_facts={"negligence_offset_issue": True},
                outcome={"disposition": "partially accepted", "key_factor": "victim fault"},
                cited_articles=["civil_act_750"],
                facets={"legal_domain": "damages"},
                evidence_spans={"facts": [{"paragraph_id": "P001"}], "reasoning": [{"paragraph_id": "P0017"}]},
                confidence_score=0.84,
            ),
            CompareCandidateRecord(
                case_id="44444444-4444-4444-4444-444444444444",
                case_no="2019Da5555",
                court_name="District Court",
                decision_date=date(2020, 1, 20),
                case_name="Unrelated contract case",
                legal_domain="contract",
                facts="A contract payment was disputed.",
                legal_issue="Payment",
                conclusion="The claim was dismissed.",
                material_facts={"negligence_offset_issue": False},
                outcome={"disposition": "dismissed", "key_factor": "contract"},
                cited_articles=["civil_act_390"],
                facets={"legal_domain": "contract"},
                evidence_spans={"reasoning": ["p04"]},
                confidence_score=0.7,
            ),
        ]

    def embedding_similarities_for_case(self, case_id: str, embedding_model: str) -> dict[str, float]:
        if case_id != CASE_ID:
            return {}
        assert embedding_model == "local-hash-embedding-v1"
        return {
            COMPARE_CASE_ID: 0.91,
            "44444444-4444-4444-4444-444444444444": 0.1,
        }


def override_case_detail_service() -> CaseDetailService:
    return CaseDetailService(FakeCaseDetailRepository())


def override_compare_service() -> CaseDetailService:
    return CaseDetailService(FakeCaseDetailRepository())


def test_get_case_detail_returns_contract_shape() -> None:
    app.dependency_overrides[get_case_detail_service] = override_case_detail_service
    client = TestClient(app)

    try:
        response = client.get(f"/api/v1/cases/{CASE_ID}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["case"]["case_id"] == CASE_ID
    assert body["case"]["case_no"] == "2021Da2345"
    assert body["structure"]["cited_articles"] == ["civil_act_750"]
    assert body["structure"]["evidence_spans"] == {"facts": ["p12"], "outcome": ["p18"]}
    assert body["paragraphs"][0]["evidence_id"] == "p12"


def test_get_case_detail_returns_404_for_unknown_case() -> None:
    app.dependency_overrides[get_case_detail_service] = override_case_detail_service
    client = TestClient(app)

    try:
        response = client.get("/api/v1/cases/22222222-2222-2222-2222-222222222222")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CASE_NOT_FOUND"


def test_get_case_rag_summary_returns_grounded_sections() -> None:
    app.dependency_overrides[get_case_detail_service] = override_case_detail_service
    client = TestClient(app)

    try:
        response = client.get(f"/api/v1/cases/{CASE_ID}/rag-summary")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["case"]["case_id"] == CASE_ID
    assert body["summary"]["generated_by"] == "local_grounded_extractive_rag"
    assert body["summary"]["fallback_used"] is True
    assert body["summary"]["facts"]["evidence_ids"] == ["p12"]
    assert "Driver negligence" in body["summary"]["facts"]["text"]
    assert body["evidence_links"][0]["evidence_id"] == "p12"


def test_get_case_rag_summary_uses_gemini_when_configured(monkeypatch) -> None:
    previous_key = settings.gemini_api_key
    previous_model = settings.gemini_model
    settings.gemini_api_key = "test-gemini-key"
    settings.gemini_model = "gemini-test-model"

    def fake_generate_case_summary(**kwargs):
        assert kwargs["api_key"] == "test-gemini-key"
        assert kwargs["model"] == "gemini-test-model"
        assert kwargs["evidence_links"][0]["evidence_id"] == "p12"
        return {
            "facts": "Gemini facts summary.",
            "issue": "Gemini issue summary.",
            "reasoning": "Gemini reasoning summary.",
            "outcome": "Gemini outcome summary.",
        }

    monkeypatch.setattr("app.services.cases.generate_case_summary", fake_generate_case_summary)
    app.dependency_overrides[get_case_detail_service] = override_case_detail_service
    client = TestClient(app)

    try:
        response = client.get(f"/api/v1/cases/{CASE_ID}/rag-summary")
    finally:
        app.dependency_overrides.clear()
        settings.gemini_api_key = previous_key
        settings.gemini_model = previous_model

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["generated_by"] == "gemini-test-model"
    assert body["summary"]["fallback_used"] is False
    assert body["summary"]["facts"]["text"] == "Gemini facts summary."


def test_get_case_rag_summary_returns_404_for_unknown_case() -> None:
    app.dependency_overrides[get_case_detail_service] = override_case_detail_service
    client = TestClient(app)

    try:
        response = client.get("/api/v1/cases/22222222-2222-2222-2222-222222222222/rag-summary")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CASE_NOT_FOUND"


def test_get_compare_candidates_returns_ranked_candidates() -> None:
    settings.embedding_provider = "local"
    settings.embedding_model = "local-hash-embedding-v1"
    app.dependency_overrides[get_case_detail_service] = override_case_detail_service
    client = TestClient(app)

    try:
        response = client.get(f"/api/v1/cases/{CASE_ID}/compare-candidates?limit=5")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["base_case"]["case_id"] == CASE_ID
    assert body["ranking_policy"]["outcome_difference_weight"] == 0.03
    assert body["candidates"][0]["case_no"] == "2020Da4321"
    assert body["candidates"][0]["scores"]["final_score"] > body["candidates"][1]["scores"]["final_score"]
    assert body["candidates"][0]["common_facts"] == ["negligence_offset_issue: True"]
    assert body["candidates"][0]["evidence_ids"] == ["P0001", "P0017"]


def test_get_compare_candidates_returns_404_for_unknown_case() -> None:
    app.dependency_overrides[get_case_detail_service] = override_case_detail_service
    client = TestClient(app)

    try:
        response = client.get(
            "/api/v1/cases/22222222-2222-2222-2222-222222222222/compare-candidates"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CASE_NOT_FOUND"


def test_compare_cases_returns_structured_fallback_analysis() -> None:
    app.dependency_overrides[get_compare_service] = override_compare_service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/compare",
            json={"base_case_id": CASE_ID, "compare_case_id": COMPARE_CASE_ID},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["base"]["case_id"] == CASE_ID
    assert body["compare"]["case_id"] == COMPARE_CASE_ID
    assert body["analysis"]["generated_by"] == "structured_fallback"
    assert body["analysis"]["fallback_used"] is True
    assert body["analysis"]["common_points"][0]["evidence_ids"]["base"] == ["p12", "p18"]
    assert body["analysis"]["material_differences"][0]["factor"] == "victim_fault"
    assert body["evidence_links"]["base"][0]["evidence_id"] == "p12"
    assert body["evidence_links"]["compare"][0]["evidence_id"] == "p08"


def test_compare_cases_returns_404_for_unknown_case() -> None:
    app.dependency_overrides[get_compare_service] = override_compare_service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/compare",
            json={
                "base_case_id": CASE_ID,
                "compare_case_id": "22222222-2222-2222-2222-222222222222",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CASE_NOT_FOUND"
