from pydantic import BaseModel


class VoiceRuntimeFlags(BaseModel):
    historian_enabled: bool = True
    color_poetics_enabled: bool = True
    deep_mode_enabled: bool = True
    cta_experimental_copy_enabled: bool = False
