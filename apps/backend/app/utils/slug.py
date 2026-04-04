from slugify import slugify


def build_slug(value: str) -> str:
    slug = slugify(value)
    return slug or "untitled"

