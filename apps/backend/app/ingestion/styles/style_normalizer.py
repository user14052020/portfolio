import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlparse

from app.ingestion.styles.contracts import (
    NormalizedImage,
    NormalizedLink,
    NormalizedSection,
    NormalizedStyleDocument,
    ScrapedStylePage,
    StyleNormalizer,
    StyleSourceRegistryEntry,
)


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


SEE_ALSO_SECTION_TERMS = ("see also", "related", "similar", "adjacent", "variants")
FAMILY_SECTION_TERMS = ("family", "families")
CATEGORY_SECTION_TERMS = ("category", "categories", "subculture")
COLOR_SECTION_TERMS = ("color", "colour", "palette")
DECADE_SECTION_TERMS = ("decade", "era")
REGION_SECTION_TERMS = ("region", "origin", "culture")
UMBRELLA_SECTION_TERMS = ("umbrella", "umbrella term")


def _decode_wiki_title(url: str) -> str | None:
    parsed = urlparse(url)
    path = parsed.path or ""
    if "/wiki/" not in path:
        return None
    slug = path.split("/wiki/", 1)[1]
    title = unquote(slug).replace("_", " ")
    cleaned = _clean_text(title)
    return cleaned or None


class _StyleHTMLParser(HTMLParser):
    def __init__(self, *, base_url: str, allowed_domains: tuple[str, ...]) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.allowed_domains = allowed_domains
        self._ignored_tag: str | None = None
        self._heading_level: int | None = None
        self._heading_parts: list[str] = []
        self._current_section_title: str | None = None
        self._current_section_level: int | None = None
        self._current_section_parts: list[str] = []
        self._all_text_parts: list[str] = []
        self._link_href: str | None = None
        self._link_parts: list[str] = []
        self.links: list[NormalizedLink] = []
        self.images: list[NormalizedImage] = []
        self.sections: list[NormalizedSection] = []

    def _resolve_internal_link_type(self) -> str:
        title = _clean_text(self._current_section_title).casefold()
        if any(term in title for term in SEE_ALSO_SECTION_TERMS):
            return "see_also"
        if any(term in title for term in FAMILY_SECTION_TERMS):
            return "family_hint"
        if any(term in title for term in CATEGORY_SECTION_TERMS):
            return "category_hint"
        if any(term in title for term in COLOR_SECTION_TERMS):
            return "color_hint"
        if any(term in title for term in DECADE_SECTION_TERMS):
            return "decade_hint"
        if any(term in title for term in REGION_SECTION_TERMS):
            return "region_hint"
        if any(term in title for term in UMBRELLA_SECTION_TERMS):
            return "umbrella_hint"
        return "wiki_internal"

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignored_tag = tag
            return
        if self._ignored_tag is not None:
            return

        attrs_map = dict(attrs)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._flush_section()
            self._heading_level = int(tag[1])
            self._heading_parts = []
            return

        if tag == "a":
            self._link_href = attrs_map.get("href")
            self._link_parts = []
            return

        if tag == "img":
            image_url = attrs_map.get("src")
            if image_url:
                self.images.append(
                    NormalizedImage(
                        image_url=urljoin(self.base_url, image_url),
                        caption=attrs_map.get("title"),
                        alt_text=attrs_map.get("alt"),
                        position=len(self.images),
                    )
                )

        if tag in {"br", "p", "li"}:
            self._append_text("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_tag == tag:
            self._ignored_tag = None
            return
        if self._ignored_tag is not None:
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._heading_level is not None:
            heading = _clean_text(" ".join(self._heading_parts))
            self._current_section_title = heading or None
            self._current_section_level = self._heading_level
            self._heading_level = None
            self._heading_parts = []
            return

        if tag == "a" and self._link_href:
            anchor_text = _clean_text(" ".join(self._link_parts)) or None
            target_url = urljoin(self.base_url, self._link_href)
            parsed = urlparse(target_url)
            link_type = "external"
            target_title = anchor_text
            if parsed.netloc.endswith(self.allowed_domains):
                link_type = self._resolve_internal_link_type()
                target_title = _decode_wiki_title(target_url) or anchor_text
            self.links.append(
                NormalizedLink(
                    anchor_text=anchor_text,
                    target_title=target_title,
                    target_url=target_url,
                    link_type=link_type,
                )
            )
            self._link_href = None
            self._link_parts = []

        if tag in {"p", "li"}:
            self._append_text("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_tag is not None:
            return
        cleaned = _clean_text(data)
        if not cleaned:
            return
        self._all_text_parts.append(cleaned)
        if self._heading_level is not None:
            self._heading_parts.append(cleaned)
            return
        self._current_section_parts.append(cleaned)
        if self._link_href:
            self._link_parts.append(cleaned)

    def finalize(self) -> tuple[str, tuple[NormalizedSection, ...], tuple[NormalizedLink, ...], tuple[NormalizedImage, ...]]:
        self._flush_section()
        raw_text = _clean_text(" ".join(self._all_text_parts))
        if not self.sections and raw_text:
            self.sections.append(
                NormalizedSection(
                    section_order=0,
                    section_title=None,
                    section_level=None,
                    section_text=raw_text,
                    section_hash=_hash_text(raw_text),
                )
            )
        return raw_text, tuple(self.sections), tuple(self.links), tuple(self.images)

    def _flush_section(self) -> None:
        section_text = _clean_text(" ".join(self._current_section_parts))
        if section_text:
            self.sections.append(
                NormalizedSection(
                    section_order=len(self.sections),
                    section_title=self._current_section_title,
                    section_level=self._current_section_level,
                    section_text=section_text,
                    section_hash=_hash_text(section_text),
                )
            )
        self._current_section_parts = []
        self._current_section_title = None
        self._current_section_level = None

    def _append_text(self, value: str) -> None:
        if value.strip():
            self._current_section_parts.append(value.strip())


class DefaultStyleNormalizer(StyleNormalizer):
    def normalize_page(
        self,
        source: StyleSourceRegistryEntry,
        page: ScrapedStylePage,
    ) -> NormalizedStyleDocument:
        parser = _StyleHTMLParser(base_url=page.source_url, allowed_domains=source.allowed_domains)
        parser.feed(page.raw_html)
        raw_text, sections, links, images = parser.finalize()
        source_hash = _hash_text(f"{page.source_url}\n{raw_text}\n{page.raw_html}")
        return NormalizedStyleDocument(
            source_name=page.source_name,
            source_site=page.source_site,
            source_title=page.source_title,
            source_url=page.source_url,
            fetched_at=page.fetched_at,
            raw_html=page.raw_html,
            raw_text=raw_text,
            source_hash=source_hash,
            sections=sections,
            links=links,
            images=images,
            parser_version=source.parser_version,
            normalizer_version=source.normalizer_version,
        )
