"""Provider registry and dependency injection container (DEV-004, ADR-004)."""

from app.config.settings import Settings, get_settings
from app.response.fakes import FakeParaphraser
from app.response.interfaces import Paraphraser
from app.speech.fakes import FakeASRProvider, FakeTTSProvider
from app.speech.interfaces import ASRProvider, TTSProvider
from app.understanding.fakes import FakeSemanticResolver
from app.understanding.interfaces import SemanticResolver
from app.vision.fakes import FakeVisionProvider
from app.vision.interfaces import VisionProvider


class ProviderRegistry:
    """Central registry for speech, understanding, response, and vision adapters."""

    def __init__(
        self,
        asr: ASRProvider,
        tts: TTSProvider,
        semantic: SemanticResolver | None = None,
        paraphraser: Paraphraser | None = None,
        vision: VisionProvider | None = None,
    ) -> None:
        self.asr = asr
        self.tts = tts
        self.semantic = semantic
        self.paraphraser = paraphraser
        self.vision = vision

    @property
    def is_semantic_enabled(self) -> bool:
        return self.semantic is not None

    @property
    def is_paraphrase_enabled(self) -> bool:
        return self.paraphraser is not None

    @property
    def is_vision_enabled(self) -> bool:
        return self.vision is not None


def create_provider_registry(settings: Settings | None = None) -> ProviderRegistry:
    """Construct provider registry configured according to runtime profile and feature flags."""
    if settings is None:
        settings = get_settings()

    # 1. ASR Provider
    asr_provider: ASRProvider = FakeASRProvider(model_version=f"asr-{settings.asr_provider}")

    # 2. TTS Provider
    tts_provider: TTSProvider = FakeTTSProvider()

    # 3. Optional Semantic Resolver (DEV-004)
    semantic_resolver: SemanticResolver | None = None
    if settings.semantic_enabled:
        semantic_resolver = FakeSemanticResolver()

    # 4. Optional LLM Paraphraser (DEV-004, AI-008)
    paraphraser: Paraphraser | None = None
    if settings.llm_paraphrase_enabled:
        paraphraser = FakeParaphraser()

    # 5. Optional Computer Vision (DEV-004, AI-009)
    vision_provider: VisionProvider | None = None
    if settings.vision_enabled:
        vision_provider = FakeVisionProvider()

    return ProviderRegistry(
        asr=asr_provider,
        tts=tts_provider,
        semantic=semantic_resolver,
        paraphraser=paraphraser,
        vision=vision_provider,
    )
