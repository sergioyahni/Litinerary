from app.models import BookLocationCandidateModel
from app.schemas.ingestion import BookLocationCandidate
from app.schemas.poi_verification import POIVerificationResultResponse


def candidate_from_model(candidate: BookLocationCandidateModel) -> BookLocationCandidate:
    return BookLocationCandidate(
        id=candidate.id,
        jobId=candidate.job_id,
        bookId=candidate.book_id,
        destinationId=candidate.destination_id,
        name=candidate.name,
        description=candidate.description,
        latitude=candidate.latitude,
        longitude=candidate.longitude,
        literaryRelevance=candidate.literary_relevance,
        confidence=candidate.confidence,
        status=candidate.status,
        promotedPoiId=candidate.promoted_poi_id,
        createdAt=candidate.created_at,
    )


def verification_result_response(
    result,
) -> POIVerificationResultResponse:
    return POIVerificationResultResponse(
        status=result.status,
        provider=result.provider,
        confidence=result.confidence,
        verifiedName=result.verified_name,
        verifiedAddress=result.verified_address,
        verifiedLatitude=result.verified_latitude,
        verifiedLongitude=result.verified_longitude,
        openingHoursNote=result.opening_hours_note,
        ticketingUrl=result.ticketing_url,
        notes=result.notes,
        providerVersion=result.metadata.provider_version if result.metadata else None,
        providerRequestId=result.metadata.request_id if result.metadata else None,
        verifiedAt=result.metadata.verified_at if result.metadata else None,
        warnings=result.metadata.warnings if result.metadata else [],
    )
