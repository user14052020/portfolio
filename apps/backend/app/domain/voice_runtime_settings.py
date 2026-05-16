from app.domain.reasoning import VoiceRuntimeFlags


class VoiceRuntimeSettings(VoiceRuntimeFlags):
    def runtime_flags(self) -> VoiceRuntimeFlags:
        return VoiceRuntimeFlags(**self.model_dump())
