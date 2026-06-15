from pydantic import BaseModel, Field

from app.schemas.domain import Book, Destination, Itinerary, POI


class SeedDataPayload(BaseModel):
    destinations: list[Destination] = Field(default_factory=list)
    books: list[Book] = Field(default_factory=list)
    pois: list[POI] = Field(default_factory=list)
    itineraries: list[Itinerary] = Field(default_factory=list)


class SeedValidationReport(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class SeedOperationResult(BaseModel):
    message: str
    counts: dict[str, int] = Field(default_factory=dict)
    validation: SeedValidationReport | None = None
