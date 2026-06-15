import pytest

from app.data.mock_data import BOOKS, DESTINATIONS, ITINERARIES, POIS
from app.schemas.domain import ItineraryGenerationRequest
from app.services.mock_ai_service import (
    MockAIServicePipeline,
    MockLLMJudgeValidationService,
)


def test_mock_ai_pipeline_generates_deterministic_candidate() -> None:
    pipeline = MockAIServicePipeline()
    request = ItineraryGenerationRequest(
        destinationId="paris",
        bookId="les-miserables",
        durationDays=2,
        transportationMode="walking",
    )
    destination = next(item for item in DESTINATIONS if item.id == "paris")
    book = next(item for item in BOOKS if item.id == "les-miserables")
    pois = [
        poi
        for poi in POIS
        if poi.destinationId == "paris" and "les-miserables" in poi.bookIds
    ]

    first = pipeline.generate_candidate_itinerary(destination, book, pois, request)
    second = pipeline.generate_candidate_itinerary(destination, book, pois, request)

    assert first == second
    assert pipeline.validate_itinerary(first).approved is True
    assert first.sourceType == "new_mock_generation"


def test_mock_judge_rejects_empty_or_malformed_itinerary() -> None:
    judge = MockLLMJudgeValidationService()
    malformed = ITINERARIES[0].model_copy(
        update={"title": "", "days": []},
        deep=True,
    )

    result = judge.validate_itinerary(malformed)

    assert result.approved is False
    assert "Title is required." in result.reasons
    assert "At least one itinerary day is required." in result.reasons


def test_mock_judge_rejects_stops_without_coordinates() -> None:
    judge = MockLLMJudgeValidationService()
    itinerary = ITINERARIES[0]
    stop = itinerary.days[0].stops[0]
    malformed_stop = stop.model_copy(
        update={"poi": stop.poi.model_copy(update={"latitude": 0.0})},
        deep=True,
    )
    malformed_day = itinerary.days[0].model_copy(
        update={"stops": [malformed_stop]},
        deep=True,
    )
    malformed = itinerary.model_copy(update={"days": [malformed_day]}, deep=True)

    result = judge.validate_itinerary(malformed)

    assert result.approved is False
    assert any("missing coordinates" in reason for reason in result.reasons)


def test_generation_endpoint_returns_clear_error_when_mock_judge_rejects(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BadPipeline:
        def generate_candidate_itinerary(self, destination, book, pois, request):
            valid = MockAIServicePipeline().generate_candidate_itinerary(
                destination,
                book,
                pois,
                request,
            )
            return valid.model_copy(update={"days": []}, deep=True)

        def validate_itinerary(self, itinerary):
            return MockLLMJudgeValidationService().validate_itinerary(itinerary)

    import app.services.mock_repository as mock_repository

    monkeypatch.setattr(mock_repository, "get_ai_pipeline", lambda: BadPipeline())

    response = client.post(
        "/api/itinerary/generate",
        json={
            "destinationId": "paris",
            "bookId": "les-miserables",
            "durationDays": 2,
            "transportationMode": "walking",
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"]["message"] == (
        "Mock AI judge rejected the candidate itinerary."
    )
    assert "At least one itinerary day is required." in response.json()["detail"]["reasons"]
