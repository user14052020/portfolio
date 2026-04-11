from pathlib import Path


WORKFLOW_DIR = Path("app/infrastructure/comfy/workflows")
WORKFLOW_TEMPLATES = {
    "fashion_flatlay_base": WORKFLOW_DIR / "fashion_flatlay_base.json",
    "garment_matching_variation": WORKFLOW_DIR / "garment_matching_variation.json",
    "style_exploration_variation": WORKFLOW_DIR / "style_exploration_variation.json",
    "occasion_outfit_variation": WORKFLOW_DIR / "occasion_outfit_variation.json",
}


def get_workflow_template(workflow_name: str) -> Path:
    return WORKFLOW_TEMPLATES.get(workflow_name, WORKFLOW_TEMPLATES["fashion_flatlay_base"])

