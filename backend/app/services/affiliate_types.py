from dataclasses import dataclass, field
from typing import Protocol

from app.services.provider_contracts import ProviderMetadata


@dataclass(frozen=True)
class AffiliateProductRequest:
    book_id: str
    title: str
    author: str
    format: str | None = None


@dataclass(frozen=True)
class AffiliateProduct:
    title: str
    source_url: str | None
    provider_product_id: str | None = None
    format: str | None = None
    affiliate: bool = False
    last_checked_at: str | None = None
    relevance_score: float | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: ProviderMetadata | None = None


class AffiliateProvider(Protocol):
    """Future book/e-commerce affiliate contract.

    Real implementations must keep affiliate disclosures visible and must not place
    payment or e-commerce secrets in frontend-exposed payloads.
    """

    def find_products(self, request: AffiliateProductRequest) -> list[AffiliateProduct]:
        """Return optional book product links for future e-commerce milestones."""

    def lookup_book_affiliate_links(
        self,
        request: AffiliateProductRequest,
    ) -> list[AffiliateProduct]:
        """Return optional book/eBook/audiobook links without checkout behavior."""
