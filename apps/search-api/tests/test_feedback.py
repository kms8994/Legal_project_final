from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.feedback import get_feedback_service
from app.main import app
from app.repositories.feedback import FeedbackInput
from app.services.feedback import FeedbackService


class FakeFeedbackRepository:
    def __init__(self) -> None:
        self.saved: FeedbackInput | None = None

    def save(self, feedback: FeedbackInput) -> str:
        self.saved = feedback
        return "55555555-5555-5555-5555-555555555555"


fake_repository = FakeFeedbackRepository()


def override_feedback_service() -> FeedbackService:
    return FeedbackService(fake_repository)


def test_save_feedback_returns_contract_shape() -> None:
    app.dependency_overrides[get_feedback_service] = override_feedback_service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/feedback",
            json={
                "base_case_id": "11111111-1111-1111-1111-111111111111",
                "compare_case_id": "33333333-3333-3333-3333-333333333333",
                "label": "facts_not_similar",
                "reason": "Different victim conduct.",
                "comment": "This candidate is weak.",
                "user_id": "anon-test",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "feedback_id": "55555555-5555-5555-5555-555555555555",
        "status": "saved",
    }
    assert fake_repository.saved is not None
    assert fake_repository.saved.label == "facts_not_similar"
    assert fake_repository.saved.user_id == "anon-test"


def test_save_feedback_rejects_unknown_label() -> None:
    app.dependency_overrides[get_feedback_service] = override_feedback_service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/feedback",
            json={
                "label": "unknown",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
