from fastapi import HTTPException


def not_found(resource: str, identifier: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Unknown {resource}: {identifier}")


def not_found_detail(detail: str) -> HTTPException:
    return HTTPException(status_code=404, detail=detail)


def validation_error(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=409, detail=detail)


def mock_judge_rejected(
    reasons: list[str],
    *,
    warnings: list[str] | None = None,
    confidence_score: float | None = None,
    required_fixes: list[str] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=500,
        detail={
            "message": "Mock AI judge rejected the candidate itinerary.",
            "reasons": reasons,
            "warnings": warnings or [],
            "confidenceScore": confidence_score,
            "requiredFixes": required_fixes or [],
        },
    )
