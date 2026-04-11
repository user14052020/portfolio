from app.domain.visual_generation import VisualPreset


VISUAL_PRESETS = {
    "editorial_studio": VisualPreset(
        id="editorial_studio",
        name="Editorial Studio",
        mode_affinity=["general_advice", "garment_matching"],
        background_family="muted studio background",
        layout_archetype="centered anchor composition",
        spacing_density="balanced",
        object_count_range="balanced outfit set",
        camera_distance="medium flat lay",
        shadow_hardness="moderate natural",
        anchor_garment_centrality="high",
        practical_coherence="medium",
        diversity_bias="low",
        tags=["studio", "readable", "controlled"],
    ),
    "airy_catalog": VisualPreset(
        id="airy_catalog",
        name="Airy Catalog",
        mode_affinity=["occasion_outfit", "style_exploration"],
        background_family="off-white linen",
        layout_archetype="catalog grid-like arrangement",
        spacing_density="airy",
        object_count_range="balanced outfit set",
        camera_distance="wider editorial overhead",
        shadow_hardness="soft diffused",
        anchor_garment_centrality="medium",
        practical_coherence="high",
        diversity_bias="medium",
        tags=["catalog", "airy", "clean"],
    ),
    "textured_surface": VisualPreset(
        id="textured_surface",
        name="Textured Surface",
        mode_affinity=["style_exploration"],
        background_family="warm wood",
        layout_archetype="diagonal editorial spread",
        spacing_density="balanced",
        object_count_range="rich layered spread",
        camera_distance="wider editorial overhead",
        shadow_hardness="crisp editorial",
        anchor_garment_centrality="medium",
        practical_coherence="medium",
        diversity_bias="high",
        tags=["editorial", "variation", "surface"],
    ),
    "dark_gallery": VisualPreset(
        id="dark_gallery",
        name="Dark Gallery",
        mode_affinity=["style_exploration", "occasion_outfit"],
        background_family="dark textured surface",
        layout_archetype="radial outfit spread",
        spacing_density="airy",
        object_count_range="rich layered spread",
        camera_distance="wider editorial overhead",
        shadow_hardness="crisp editorial",
        anchor_garment_centrality="medium",
        practical_coherence="medium",
        diversity_bias="high",
        tags=["gallery", "dramatic", "diverse"],
    ),
    "practical_board": VisualPreset(
        id="practical_board",
        name="Practical Board",
        mode_affinity=["occasion_outfit"],
        background_family="neutral paper",
        layout_archetype="practical dressing board",
        spacing_density="balanced",
        object_count_range="balanced outfit set",
        camera_distance="medium flat lay",
        shadow_hardness="soft diffused",
        anchor_garment_centrality="medium",
        practical_coherence="high",
        diversity_bias="low",
        tags=["practical", "occasion", "coherent"],
    ),
}


def list_visual_presets() -> list[VisualPreset]:
    return [preset.model_copy(deep=True) for preset in VISUAL_PRESETS.values()]


def get_visual_preset(preset_id: str) -> VisualPreset | None:
    preset = VISUAL_PRESETS.get(preset_id)
    return preset.model_copy(deep=True) if preset is not None else None

