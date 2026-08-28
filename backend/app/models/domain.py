from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


book_destinations = Table(
    "book_destinations",
    Base.metadata,
    Column("book_id", ForeignKey("books.id"), primary_key=True),
    Column("destination_id", ForeignKey("destinations.id"), primary_key=True),
)

poi_books = Table(
    "poi_books",
    Base.metadata,
    Column("poi_id", ForeignKey("pois.id"), primary_key=True),
    Column("book_id", ForeignKey("books.id"), primary_key=True),
)

user_bookmarks = Table(
    "user_bookmarks",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("itinerary_id", ForeignKey("itineraries.id"), primary_key=True),
)


class DestinationModel(Base):
    __tablename__ = "destinations"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))
    supported: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    books: Mapped[list["BookModel"]] = relationship(
        secondary=book_destinations,
        back_populates="destinations",
    )
    pois: Mapped[list["POIModel"]] = relationship(back_populates="destination")
    itineraries: Mapped[list["ItineraryModel"]] = relationship(back_populates="destination")


class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    publication_year: Mapped[int | None] = mapped_column(Integer)
    public_domain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    themes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    cover_url: Mapped[str | None] = mapped_column(String(500))

    destinations: Mapped[list[DestinationModel]] = relationship(
        secondary=book_destinations,
        back_populates="books",
    )
    pois: Mapped[list["POIModel"]] = relationship(
        secondary=poi_books,
        back_populates="books",
    )
    itineraries: Mapped[list["ItineraryModel"]] = relationship(back_populates="book")
    ingestion_sources: Mapped[list["BookSourceModel"]] = relationship(
        back_populates="book",
        cascade="all, delete-orphan",
    )
    ingestion_jobs: Mapped[list["BookIngestionJobModel"]] = relationship(
        back_populates="book",
        cascade="all, delete-orphan",
    )


class POIModel(Base):
    __tablename__ = "pois"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str | None] = mapped_column(String(500))
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    ticketing_note: Mapped[str | None] = mapped_column(Text)
    literary_relevance: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_provider: Mapped[str | None] = mapped_column(String(80))
    provider_version: Mapped[str | None] = mapped_column(String(120))
    provider_request_id: Mapped[str | None] = mapped_column(String(180))
    verification_confidence: Mapped[float | None] = mapped_column(Float)
    verified_name: Mapped[str | None] = mapped_column(String(255))
    verified_address: Mapped[str | None] = mapped_column(String(500))
    verified_latitude: Mapped[float | None] = mapped_column(Float)
    verified_longitude: Mapped[float | None] = mapped_column(Float)
    opening_hours_note: Mapped[str | None] = mapped_column(Text)
    ticketing_url: Mapped[str | None] = mapped_column(String(500))
    verification_notes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    last_verified_at: Mapped[str | None] = mapped_column(String(80))
    manual_review_status: Mapped[str] = mapped_column(
        String(40), default="not_reviewed", nullable=False
    )
    reviewed_by_user_id: Mapped[str | None] = mapped_column(String(120))
    provenance_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    destination: Mapped[DestinationModel] = relationship(back_populates="pois")
    books: Mapped[list[BookModel]] = relationship(
        secondary=poi_books,
        back_populates="pois",
    )
    itinerary_stops: Mapped[list["ItineraryStopModel"]] = relationship(back_populates="poi")


class ItineraryModel(Base):
    __tablename__ = "itineraries"
    __table_args__ = (
        Index("ix_itineraries_public_visibility", "is_public", "visibility"),
        Index("ix_itineraries_owner_visibility", "owner_user_id", "visibility"),
    )

    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.id"), nullable=False)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    transportation_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    visibility: Mapped[str] = mapped_column(String(40), default="public", nullable=False)
    generated_from: Mapped[str] = mapped_column(String(40), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(60))
    source_itinerary_id: Mapped[str | None] = mapped_column(String(180))
    created_by_mode: Mapped[str] = mapped_column(String(40), default="anonymous", nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(String(120))
    subscriber_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    adaptation_notes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)
    updated_at: Mapped[str | None] = mapped_column(String(80))
    provider_name: Mapped[str | None] = mapped_column(String(80))
    provider_type: Mapped[str | None] = mapped_column(String(80))
    provider_version: Mapped[str | None] = mapped_column(String(120))
    provider_request_id: Mapped[str | None] = mapped_column(String(180))
    generated_by_service: Mapped[str | None] = mapped_column(String(120))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    provenance_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    destination: Mapped[DestinationModel] = relationship(back_populates="itineraries")
    book: Mapped[BookModel] = relationship(back_populates="itineraries")
    days: Mapped[list["ItineraryDayModel"]] = relationship(
        back_populates="itinerary",
        cascade="all, delete-orphan",
        order_by="ItineraryDayModel.day_number",
    )
    bookmarked_by: Mapped[list["UserModel"]] = relationship(
        secondary=user_bookmarks,
        back_populates="bookmarked_itineraries",
    )
    owner: Mapped["UserModel | None"] = relationship(
        back_populates="owned_itineraries",
        foreign_keys=[owner_user_id],
    )


class ItineraryDayModel(Base):
    __tablename__ = "itinerary_days"

    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    itinerary_id: Mapped[str] = mapped_column(ForeignKey("itineraries.id"), nullable=False)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_distance_km: Mapped[float | None] = mapped_column(Float)
    estimated_duration_hours: Mapped[float | None] = mapped_column(Float)
    route_geometry: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    routing_provider_metadata: Mapped[dict | None] = mapped_column(JSON)
    routing_warnings: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    itinerary: Mapped[ItineraryModel] = relationship(back_populates="days")
    stops: Mapped[list["ItineraryStopModel"]] = relationship(
        back_populates="day",
        cascade="all, delete-orphan",
        order_by="ItineraryStopModel.order",
    )


class ItineraryStopModel(Base):
    __tablename__ = "itinerary_stops"

    id: Mapped[str] = mapped_column(String(220), primary_key=True)
    day_id: Mapped[str] = mapped_column(ForeignKey("itinerary_days.id"), nullable=False)
    poi_id: Mapped[str] = mapped_column(ForeignKey("pois.id"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    narrative_note: Mapped[str] = mapped_column(Text, nullable=False)
    logistics_note: Mapped[str | None] = mapped_column(Text)
    estimated_start_time: Mapped[str | None] = mapped_column(String(40))
    estimated_end_time: Mapped[str | None] = mapped_column(String(40))

    day: Mapped[ItineraryDayModel] = relationship(back_populates="stops")
    poi: Mapped[POIModel] = relationship(back_populates="itinerary_stops")


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    auth_provider: Mapped[str | None] = mapped_column(String(80))
    auth_subject: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="user", nullable=False)
    subscription_status: Mapped[str] = mapped_column(String(40), default="none", nullable=False)
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)
    updated_at: Mapped[str | None] = mapped_column(String(80))

    preferences: Mapped[list["UserPreferenceModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[list["UserReviewModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    bookmarked_itineraries: Mapped[list[ItineraryModel]] = relationship(
        secondary=user_bookmarks,
        back_populates="bookmarked_by",
    )
    owned_itineraries: Mapped[list[ItineraryModel]] = relationship(
        back_populates="owner",
        foreign_keys="ItineraryModel.owner_user_id",
        passive_deletes=True,
    )
    chat_sessions: Mapped[list["ChatSessionModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserPreferenceModel(Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)

    user: Mapped[UserModel] = relationship(back_populates="preferences")


class UserReviewModel(Base):
    __tablename__ = "user_reviews"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    itinerary_id: Mapped[str | None] = mapped_column(ForeignKey("itineraries.id"))
    rating: Mapped[int | None] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)

    user: Mapped[UserModel] = relationship(back_populates="reviews")


class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(80))
    provider_type: Mapped[str | None] = mapped_column(String(80))
    provider_version: Mapped[str | None] = mapped_column(String(120))
    provider_request_id: Mapped[str | None] = mapped_column(String(180))
    provenance_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped[UserModel] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["ChatMessageModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessageModel.created_at",
    )
    itinerary_references: Mapped[list["ChatItineraryReferenceModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatItineraryReferenceModel.created_at",
    )


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(80))
    provider_type: Mapped[str | None] = mapped_column(String(80))
    provider_version: Mapped[str | None] = mapped_column(String(120))
    provider_request_id: Mapped[str | None] = mapped_column(String(180))
    provenance_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    session: Mapped[ChatSessionModel] = relationship(back_populates="messages")


class ChatItineraryReferenceModel(Base):
    __tablename__ = "chat_itinerary_references"

    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False)
    itinerary_id: Mapped[str] = mapped_column(String(180), nullable=False)
    source_itinerary_id: Mapped[str | None] = mapped_column(String(180))
    refinement_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(80))
    provider_type: Mapped[str | None] = mapped_column(String(80))
    provider_version: Mapped[str | None] = mapped_column(String(120))
    provider_request_id: Mapped[str | None] = mapped_column(String(180))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    provenance_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    session: Mapped[ChatSessionModel] = relationship(back_populates="itinerary_references")


class BookSourceModel(Base):
    __tablename__ = "book_sources"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    reference_url: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_license: Mapped[str | None] = mapped_column(String(120))
    copyright_status: Mapped[str] = mapped_column(String(80), default="unknown", nullable=False)
    allowed_processing_mode: Mapped[str] = mapped_column(
        String(80), default="metadata_only", nullable=False
    )
    source_notes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)

    book: Mapped[BookModel] = relationship(back_populates="ingestion_sources")
    jobs: Mapped[list["BookIngestionJobModel"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
    )


class BookIngestionJobModel(Base):
    __tablename__ = "book_ingestion_jobs"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("book_sources.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    extraction_notes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(80), nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String(80))

    book: Mapped[BookModel] = relationship(back_populates="ingestion_jobs")
    source: Mapped[BookSourceModel] = relationship(back_populates="jobs")
    candidates: Mapped[list["BookLocationCandidateModel"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    artifacts: Mapped[list["BookProcessingArtifactModel"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )


class BookLocationCandidateModel(Base):
    __tablename__ = "book_location_candidates"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("book_ingestion_jobs.id"), nullable=False)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id"), nullable=False)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    literary_relevance: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    promoted_poi_id: Mapped[str | None] = mapped_column(ForeignKey("pois.id"))
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)

    job: Mapped[BookIngestionJobModel] = relationship(back_populates="candidates")
    book: Mapped[BookModel] = relationship()
    destination: Mapped[DestinationModel] = relationship()
    promoted_poi: Mapped[POIModel | None] = relationship()


class BookProcessingArtifactModel(Base):
    __tablename__ = "book_processing_artifacts"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("book_ingestion_jobs.id"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(80))
    provider_type: Mapped[str | None] = mapped_column(String(80))
    provider_version: Mapped[str | None] = mapped_column(String(120))
    provider_request_id: Mapped[str | None] = mapped_column(String(180))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    provenance_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)

    job: Mapped[BookIngestionJobModel] = relationship(back_populates="artifacts")


class EmbeddingRecordModel(Base):
    __tablename__ = "embedding_records"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    source_resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_resource_id: Mapped[str] = mapped_column(String(180), nullable=False)
    collection_name: Mapped[str] = mapped_column(String(120), nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(120), nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(160))
    vector_dimension: Mapped[int | None] = mapped_column(Integer)
    vector_external_id: Mapped[str | None] = mapped_column(String(255))
    last_embedded_at: Mapped[str | None] = mapped_column(String(80))
    metadata_version: Mapped[str] = mapped_column(String(40), default="1", nullable=False)
    provenance_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class UsageLimitCounterModel(Base):
    __tablename__ = "usage_limit_counters"
    __table_args__ = (
        UniqueConstraint(
            "subject_type",
            "subject_key",
            "action",
            "window_start",
            name="uq_usage_limit_counter_window",
        ),
        Index("ix_usage_limit_counters_subject_action", "subject_type", "subject_key", "action"),
        Index("ix_usage_limit_counters_window_end", "window_end"),
    )

    id: Mapped[str] = mapped_column(String(240), primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(180), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    window_start: Mapped[str] = mapped_column(String(40), nullable=False)
    window_end: Mapped[str] = mapped_column(String(40), nullable=False)
    units_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    limit_units: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(80), nullable=False)
