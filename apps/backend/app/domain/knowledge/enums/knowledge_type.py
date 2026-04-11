from enum import Enum


class KnowledgeType(str, Enum):
    STYLE_CATALOG = "style_catalog"
    COLOR_THEORY = "color_theory"
    FASHION_HISTORY = "fashion_history"
    TAILORING_PRINCIPLES = "tailoring_principles"
    MATERIALS_FABRICS = "materials_fabrics"
    FLATLAY_PROMPT_PATTERNS = "flatlay_prompt_patterns"
