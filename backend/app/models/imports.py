from sqlalchemy import Boolean, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ItineraryImportJobModel(Base):
    __tablename__ = "itinerary_import_jobs"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    batch_identity: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    contract_version: Mapped[str] = mapped_column(String(80), nullable=False)
    initiated_by_user_id: Mapped[str] = mapped_column(String(120), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    preview_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    persisted_itinerary_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    published_itinerary_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    error_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(80), nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String(80))

    records: Mapped[list["ItineraryImportRecordModel"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )


class ItineraryImportRecordModel(Base):
    __tablename__ = "itinerary_import_records"
    __table_args__ = (
        UniqueConstraint("source_identity", name="uq_itinerary_import_records_source_identity"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("itinerary_import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_identity: Mapped[str] = mapped_column(String(180), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(80), nullable=False)
    itinerary_id: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    publication_intent: Mapped[str] = mapped_column(String(40), nullable=False)
    source_attribution: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[str] = mapped_column(String(80), nullable=False)
    published_at: Mapped[str | None] = mapped_column(String(80))

    job: Mapped[ItineraryImportJobModel] = relationship(back_populates="records")
