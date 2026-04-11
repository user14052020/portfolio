from .common import BASE_NEGATIVE_PROMPT, BASE_PROMPT


TEMPLATE = {
    "base_prompt": BASE_PROMPT,
    "mode_prompt": "Prioritize event suitability, dress code coherence, desired impression, and practical readability for the occasion.",
    "base_negative_prompt": BASE_NEGATIVE_PROMPT + "; no underdressing or occasion-inappropriate garments",
    "default_visual_preset": "airy_catalog",
}
