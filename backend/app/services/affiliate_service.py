from functools import lru_cache

from app.core.config import get_settings
from app.services.affiliate_types import (
    AffiliateProduct,
    AffiliateProductRequest,
    AffiliateProvider,
)
from app.services.provider_contracts import ProviderMetadata, ProviderType, utc_now_iso


class MockAffiliateProvider:
    provider_name = "mock_affiliate"

    def __init__(self, base_url: str = "https://example.test/books") -> None:
        self.base_url = base_url.rstrip("/")

    def find_products(self, request: AffiliateProductRequest) -> list[AffiliateProduct]:
        return self.lookup_book_affiliate_links(request)

    def lookup_book_affiliate_links(
        self,
        request: AffiliateProductRequest,
    ) -> list[AffiliateProduct]:
        formats = [request.format] if request.format else ["print", "ebook", "audiobook"]
        return [
            self._product_for_format(request, product_format)
            for product_format in formats
            if product_format
        ]

    def _product_for_format(
        self,
        request: AffiliateProductRequest,
        product_format: str,
    ) -> AffiliateProduct:
        slug = _slugify(f"{request.title}-{request.author}-{product_format}")
        source_url = f"{self.base_url}/{slug}"
        checked_at = utc_now_iso()
        return AffiliateProduct(
            title=f"{request.title} ({product_format})",
            source_url=source_url,
            provider_product_id=f"mock-{slug}",
            format=product_format,
            affiliate=True,
            last_checked_at=checked_at,
            relevance_score=0.35,
            warnings=[
                "Mock affiliate placeholder only; no purchase, checkout, or provider lookup occurred.",
            ],
            metadata=ProviderMetadata(
                provider_name=self.provider_name,
                provider_type=ProviderType.AFFILIATE.value,
                provider_version="local-mock",
                confidence_score=0.35,
                source_url=source_url,
                generated_at=checked_at,
                warnings=["No external affiliate provider call was made."],
            ),
        )


@lru_cache
def get_affiliate_provider() -> AffiliateProvider:
    settings = get_settings()
    if settings.enable_affiliate_links:
        validate_affiliate_startup(settings)
    if settings.affiliate_provider == "mock" and not settings.enable_mock_services:
        raise RuntimeError(
            "Mock affiliate services are disabled in this environment. "
            "Set ENABLE_MOCK_SERVICES=true only for intentional local/test use."
        )
    if settings.affiliate_provider != "mock" and not settings.enable_affiliate_links:
        raise RuntimeError(
            f"Affiliate provider '{settings.affiliate_provider}' is disabled by ENABLE_AFFILIATE_LINKS."
        )
    if settings.affiliate_provider != "mock":
        raise RuntimeError(
            f"Affiliate provider '{settings.affiliate_provider}' is configured but not implemented."
        )
    return MockAffiliateProvider(settings.affiliate_base_url)


def validate_affiliate_startup(settings=None) -> None:
    resolved = settings or get_settings()
    if not resolved.enable_affiliate_links:
        return
    if resolved.affiliate_provider == "mock":
        return
    missing = []
    if not resolved.affiliate_api_key:
        missing.append("AFFILIATE_API_KEY")
    if not resolved.affiliate_base_url:
        missing.append("AFFILIATE_BASE_URL")
    if resolved.affiliate_timeout_seconds <= 0:
        missing.append("AFFILIATE_TIMEOUT_SECONDS must be positive")
    if missing:
        raise RuntimeError(
            "Real affiliate links are enabled but configuration is incomplete: "
            + ", ".join(missing)
        )
    raise RuntimeError(
        f"Affiliate provider '{resolved.affiliate_provider}' is configured, but no real "
        "affiliate adapter is implemented yet."
    )


def _slugify(value: str) -> str:
    slug = "-".join(value.strip().lower().split())
    return slug or "unknown"
