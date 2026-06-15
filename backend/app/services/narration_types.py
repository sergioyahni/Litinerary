from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.schemas.domain import Itinerary
from app.services.provider_contracts import ProviderMetadata


NarrationFormat = Literal["text_only", "placeholder_audio"]


@dataclass(frozen=True)
class NarrationScriptRequest:
    itinerary: Itinerary
    voice_style: str = "warm_literary"
    max_minutes: int | None = None


@dataclass(frozen=True)
class NarrationScript:
    itinerary_id: str
    title: str
    text: str
    estimated_duration_seconds: int
    metadata: ProviderMetadata | None = None


@dataclass(frozen=True)
class TextToSpeechRequest:
    itinerary_id: str
    text: str
    voice_name: str = "local-placeholder"
    audio_format: str = "mp3"


@dataclass(frozen=True)
class AudioMetadata:
    available: bool
    url: str | None = None
    format: str | None = None
    duration_seconds: int | None = None
    provider_name: str = "mock_tts"
    provider_type: str = "tts"
    provider_version: str = "local-mock"
    placeholder: bool = True
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NarrationResult:
    itinerary_id: str
    script: NarrationScript
    audio: AudioMetadata
    format: NarrationFormat = "text_only"


class NarrationScriptGenerationService(Protocol):
    def generate_script(self, request: NarrationScriptRequest) -> NarrationScript:
        """Create narration text from provider-neutral itinerary data."""


class TextToSpeechSynthesisService(Protocol):
    def synthesize(self, request: TextToSpeechRequest) -> AudioMetadata:
        """Return provider-neutral audio metadata without exposing provider internals."""
