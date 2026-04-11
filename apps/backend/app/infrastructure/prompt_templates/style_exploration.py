from .common import BASE_NEGATIVE_PROMPT, BASE_PROMPT


TEMPLATE = {
    "base_prompt": BASE_PROMPT,
    "mode_prompt": "Deliberately shift palette, silhouette, hero garments, and visual preset away from the recent style history while keeping one coherent visual anchor.",
    "base_negative_prompt": BASE_NEGATIVE_PROMPT + "; no repetition of the recent palette, silhouette, hero garments, or layout",
    "default_visual_preset": "textured_surface",
}
