from .common import BASE_NEGATIVE_PROMPT, BASE_PROMPT


TEMPLATE = {
    "base_prompt": BASE_PROMPT,
    "mode_prompt": "Anchor garment centrality must stay high while the rest of the outfit supports compatibility, silhouette balance, and color harmony.",
    "base_negative_prompt": BASE_NEGATIVE_PROMPT + "; no style drift away from the anchor garment",
    "default_visual_preset": "editorial_studio",
}
