from typing import Any


def merge_profile_context_sources(
    *,
    explicit_profile_context: dict[str, Any] | None,
    derived_profile_context: dict[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}

    if isinstance(derived_profile_context, dict):
        merged.update(
            {
                key: value
                for key, value in derived_profile_context.items()
                if value is not None
            }
        )

    if isinstance(explicit_profile_context, dict):
        merged.update(
            {
                key: value
                for key, value in explicit_profile_context.items()
                if value is not None
            }
        )

    return merged
