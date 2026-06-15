from sqlalchemy import select

from app.models import EmbeddingRecordModel, ItineraryModel, POIModel
from app.services import database_repository
from app.services.ingestion_service import ingestion_service
from app.services.poi_verification import verify_poi
from app.services.user_repository import create_user
from app.schemas.ingestion import BookIngestionJobCreate, BookSourceCreate
from app.schemas.users import UserCreateRequest


def test_seeded_itineraries_have_visibility_and_provenance_defaults(db_session) -> None:
    itinerary = database_repository.get_itinerary(
        db_session,
        "it-london-oliver-twist-1-walking",
    )
    row = db_session.get(ItineraryModel, "it-london-oliver-twist-1-walking")

    assert itinerary is not None
    assert itinerary.isPublic is True
    assert itinerary.visibility == "public"
    assert itinerary.createdByMode == "seed"
    assert itinerary.ownerUserId is None
    assert itinerary.subscriberOnly is False
    assert itinerary.providerName == "mock_local"
    assert itinerary.provenanceMetadata["externalProviderUsed"] is False
    assert row is not None
    assert row.provider_request_id == "seed-itinerary-it-london-oliver-twist-1-walking"


def test_private_itineraries_are_not_exposed_by_public_repository(client, db_session) -> None:
    private = ItineraryModel(
        id="it-private-reader-draft",
        destination_id="london",
        book_id="oliver-twist",
        title="Private reader draft",
        summary="A private itinerary draft.",
        duration_days=1,
        transportation_mode="walking",
        is_public=False,
        owner_user_id="dev-reader",
        visibility="private",
        generated_from="new_generation",
        source_type="new_mock_generation",
        source_itinerary_id="it-london-oliver-twist-1-walking",
        created_by_mode="registered_user",
        subscriber_only=False,
        adaptation_notes=[],
        created_at="2026-06-12T00:00:00+00:00",
        provenance_metadata={},
    )
    db_session.add(private)
    db_session.commit()

    listing = client.get("/api/itineraries")
    detail = client.get("/api/itineraries/it-private-reader-draft")

    assert listing.status_code == 200
    assert "it-private-reader-draft" not in {item["id"] for item in listing.json()}
    assert detail.status_code == 404


def test_user_profile_includes_auth_role_and_subscription_fields(db_session) -> None:
    profile = create_user(
        db_session,
        UserCreateRequest(
            id="dev-reader-model-fields",
            email="reader-model-fields@example.test",
            displayName="Reader Model Fields",
        ),
    )

    assert profile.authProvider == "dev"
    assert profile.role == "user"
    assert profile.subscriptionStatus == "none"
    assert profile.updatedAt is not None


def test_ingestion_source_licensing_and_artifact_provenance_round_trip(db_session) -> None:
    job = ingestion_service.create_job(
        db_session,
        BookIngestionJobCreate(
            bookId="oliver-twist",
            source=BookSourceCreate(
                sourceType="summary_document",
                title="Safe summary metadata",
                metadata={"summary": "Safe summary only."},
                sourceLicense="curated-summary",
                copyrightStatus="copyrighted",
                allowedProcessingMode="summary_only",
                sourceNotes=["No full text stored."],
            ),
        ),
    )
    processed = ingestion_service.run_job(db_session, job.id)

    assert processed.source.sourceLicense == "curated-summary"
    assert processed.source.copyrightStatus == "copyrighted"
    assert processed.source.allowedProcessingMode == "summary_only"
    assert processed.source.sourceNotes == ["No full text stored."]
    assert processed.artifacts
    assert processed.artifacts[0].providerName == "mock_local"
    assert processed.artifacts[0].provenanceMetadata["externalCalls"] is False


def test_poi_verification_state_and_provenance_fields_are_persisted(db_session) -> None:
    result = verify_poi(db_session, "smithfield-market")
    row = db_session.scalars(
        select(POIModel).where(POIModel.id == "smithfield-market")
    ).first()
    poi = database_repository.poi_from_model(row)

    assert result.provider == "mock_local"
    assert row is not None
    assert row.provider_version == "local-mock"
    assert row.provider_request_id is not None
    assert row.last_verified_at is not None
    assert row.manual_review_status == "not_reviewed"
    assert poi.verificationStatus == "mock_verified"
    assert poi.providerVersion == "local-mock"
    assert poi.provenanceMetadata["externalProviderUsed"] is False


def test_embedding_record_model_supports_future_vector_metadata(db_session) -> None:
    record = EmbeddingRecordModel(
        id="embedding-itinerary-smithfield",
        source_resource_type="itinerary",
        source_resource_id="it-london-oliver-twist-1-walking",
        collection_name="itineraries",
        embedding_provider="fake_vector",
        embedding_model="local-deterministic",
        vector_dimension=16,
        vector_external_id="external-itinerary-smithfield",
        last_embedded_at="2026-06-12T00:00:00+00:00",
        metadata_version="1",
        provenance_metadata={"externalProviderUsed": False},
    )
    db_session.add(record)
    db_session.commit()

    saved = db_session.get(EmbeddingRecordModel, "embedding-itinerary-smithfield")

    assert saved is not None
    assert saved.collection_name == "itineraries"
    assert saved.vector_dimension == 16
    assert saved.provenance_metadata["externalProviderUsed"] is False
