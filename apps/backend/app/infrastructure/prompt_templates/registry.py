from .garment_matching import TEMPLATE as GARMENT_MATCHING_TEMPLATE
from .general_advice import TEMPLATE as GENERAL_ADVICE_TEMPLATE
from .occasion_outfit import TEMPLATE as OCCASION_OUTFIT_TEMPLATE
from .style_exploration import TEMPLATE as STYLE_EXPLORATION_TEMPLATE


PROMPT_TEMPLATES = {
    "general_advice": GENERAL_ADVICE_TEMPLATE,
    "garment_matching": GARMENT_MATCHING_TEMPLATE,
    "style_exploration": STYLE_EXPLORATION_TEMPLATE,
    "occasion_outfit": OCCASION_OUTFIT_TEMPLATE,
}


def get_prompt_template(mode: str) -> dict[str, str]:
    return PROMPT_TEMPLATES.get(mode, GENERAL_ADVICE_TEMPLATE)
