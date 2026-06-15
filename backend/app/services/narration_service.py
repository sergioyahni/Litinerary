from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.observability import record_provider_selection
from app.core.provider_guards import require_external_call_allowed
from app.schemas.domain import Itinerary
from app.schemas.narration import (
    AudioMetadataResponse,
    ItineraryNarrationResponse,
    NarrationRequest,
    NarrationScriptResponse,
)
from app.services.narration_types import (
    AudioMetadata,
    NarrationResult,
    NarrationScript,
    NarrationScriptRequest,
    TextToSpeechRequest,
)
from app.services.provider_contracts import (
    ProviderError,
    ProviderErrorCode,
    ProviderMetadata,
    ProviderType,
)
from app.services.usage_policy import get_usage_guard


MOCK_TTS_PROVIDER_NAME = "mock_tts"


class MockNarrationService:
    def generate(self, itinerary: Itinerary, request: NarrationRequest) -> NarrationResult:
        script = self.generate_script(
            NarrationScriptRequest(
                itinerary=itinerary,
                voice_style=request.voiceStyle,
            )
        )
        get_usage_guard().guard_tts_narration(text=script.text)
        audio = self.synthesize(
            TextToSpeechRequest(
                itinerary_id=itinerary.id,
                text=script.text,
            )
        )
        if not request.includePlaceholderAudio:
            audio = AudioMetadata(
                available=False,
                duration_seconds=script.estimated_duration_seconds,
                warnings=[
                    "Real text-to-speech is disabled; text narration is available."
                ],
            )
        return NarrationResult(
            itinerary_id=itinerary.id,
            script=script,
            audio=audio,
            format="placeholder_audio" if audio.available else "text_only",
        )

    def generate_script(self, request: NarrationScriptRequest) -> NarrationScript:
        itinerary = request.itinerary
        sections = [
            f"{itinerary.title}.",
            itinerary.summary,
            (
                f"This {itinerary.durationDays}-day route is designed for "
                f"{itinerary.transportationMode.replace('_', ' ')}."
            ),
        ]

        for day in itinerary.days:
            stop_names = ", ".join(stop.poi.name for stop in day.stops)
            sections.append(f"Day {day.dayNumber}: {day.title}. {day.summary}")
            if stop_names:
                sections.append(f"Today's stops are {stop_names}.")
            for stop in day.stops:
                sections.append(
                    f"Stop {stop.order}, {stop.title}. {stop.narrativeNote}"
                )
                if stop.logisticsNote:
                    sections.append(f"Travel note: {stop.logisticsNote}")

        text = "\n\n".join(section.strip() for section in sections if section.strip())
        metadata = ProviderMetadata.mock(
            provider_name=MOCK_TTS_PROVIDER_NAME,
            provider_type=ProviderType.TTS,
            confidence_score=1.0,
            warnings=["Mock narration script generated locally."],
        )
        return NarrationScript(
            itinerary_id=itinerary.id,
            title=f"Narration for {itinerary.title}",
            text=text,
            estimated_duration_seconds=_estimate_duration_seconds(text),
            metadata=metadata,
        )

    def synthesize(self, request: TextToSpeechRequest) -> AudioMetadata:
        return AudioMetadata(
            available=True,
            url=None,
            format=request.audio_format,
            duration_seconds=_estimate_duration_seconds(request.text),
            warnings=[
                "Placeholder metadata only; no generated audio file is stored or served."
            ],
        )


@lru_cache
def get_narration_service() -> MockNarrationService:
    settings = get_settings()
    if settings.tts_provider not in {"mock", "fake", "none"}:
        if settings.enable_real_tts:
            require_external_call_allowed(
                provider_name=settings.tts_provider,
                provider_type=ProviderType.TTS,
                feature_flag_name="ENABLE_REAL_TTS",
                feature_enabled=settings.enable_real_tts,
                required_config={"TTS_API_KEY or TEXT_TO_SPEECH_API_KEY": settings.tts_api_key},
                settings=settings,
            )
            raise ProviderError(
                ProviderErrorCode.REAL_PROVIDER_DISABLED,
                (
                    f"TTS provider '{settings.tts_provider}' is configured, "
                    "but no real TTS adapter is implemented yet."
                ),
                metadata=ProviderMetadata(
                    provider_name=settings.tts_provider,
                    provider_type=ProviderType.TTS.value,
                ),
            )
        raise RuntimeError(
            "TTS_PROVIDER is non-mock but ENABLE_REAL_TTS is false; "
            "mock_tts remains the only available narration provider."
        )
    record_provider_selection(
        provider_type=ProviderType.TTS.value,
        provider_name=MOCK_TTS_PROVIDER_NAME,
        mode="mock",
    )
    return MockNarrationService()


def build_itinerary_narration(
    itinerary: Itinerary,
    request: NarrationRequest | None = None,
) -> ItineraryNarrationResponse:
    result = get_narration_service().generate(itinerary, request or NarrationRequest())
    metadata = result.script.metadata.public_dict() if result.script.metadata else {}
    return ItineraryNarrationResponse(
        itineraryId=result.itinerary_id,
        script=NarrationScriptResponse(
            itineraryId=result.script.itinerary_id,
            title=result.script.title,
            text=result.script.text,
            estimatedDurationSeconds=result.script.estimated_duration_seconds,
            providerName=metadata.get("provider_name"),
            providerType=metadata.get("provider_type"),
            providerVersion=metadata.get("provider_version"),
            providerRequestId=metadata.get("request_id"),
            provenanceMetadata=metadata,
        ),
        audio=AudioMetadataResponse(
            available=result.audio.available,
            url=result.audio.url,
            format=result.audio.format,
            durationSeconds=result.audio.duration_seconds,
            providerName=result.audio.provider_name,
            providerType=result.audio.provider_type,
            providerVersion=result.audio.provider_version,
            placeholder=result.audio.placeholder,
            warnings=result.audio.warnings,
        ),
        format=result.format,
    )


def validate_tts_startup(settings: Settings) -> list[str]:
    notes: list[str] = []
    if settings.enable_real_tts:
        try:
            require_external_call_allowed(
                provider_name=settings.tts_provider,
                provider_type=ProviderType.TTS,
                feature_flag_name="ENABLE_REAL_TTS",
                feature_enabled=settings.enable_real_tts,
                required_config={"TTS_API_KEY or TEXT_TO_SPEECH_API_KEY": settings.tts_api_key},
                settings=settings,
            )
        except ProviderError as exc:
            notes.append(exc.message)
        notes.append(
            "ENABLE_REAL_TTS=true is configured, but no real TTS adapter is implemented; "
            "mock narration remains the only safe provider."
        )
    if settings.tts_provider not in {"mock", "fake", "none"} and not settings.tts_api_key:
        notes.append(
            f"TTS provider '{settings.tts_provider}' is configured without credentials; "
            "real integration calls are not available."
        )
    return notes


def _estimate_duration_seconds(text: str) -> int:
    words = len(text.split())
    return max(15, round((words / 150) * 60))
