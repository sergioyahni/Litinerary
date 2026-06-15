from pydantic import BaseModel, Field


class NarrationRequest(BaseModel):
    voiceStyle: str = "warm_literary"
    includePlaceholderAudio: bool = False


class NarrationScriptResponse(BaseModel):
    itineraryId: str
    title: str
    text: str
    estimatedDurationSeconds: int
    providerName: str | None = None
    providerType: str | None = None
    providerVersion: str | None = None
    providerRequestId: str | None = None
    provenanceMetadata: dict = Field(default_factory=dict)


class AudioMetadataResponse(BaseModel):
    available: bool
    url: str | None = None
    format: str | None = None
    durationSeconds: int | None = None
    providerName: str = "mock_tts"
    providerType: str = "tts"
    providerVersion: str = "local-mock"
    placeholder: bool = True
    warnings: list[str] = Field(default_factory=list)


class ItineraryNarrationResponse(BaseModel):
    itineraryId: str
    script: NarrationScriptResponse
    audio: AudioMetadataResponse
    format: str = "text_only"
