from dataclasses import dataclass


@dataclass(frozen=True)
class LocaleTextValidation:
    is_valid: bool
    reason: str | None = None


class LocaleTextPolicy:
    """Validates user-facing assistant prose against the requested locale."""

    _CJK_RANGES = (
        (0x3040, 0x30FF),  # Hiragana, Katakana
        (0x3400, 0x4DBF),  # CJK Extension A
        (0x4E00, 0x9FFF),  # CJK Unified Ideographs
        (0xAC00, 0xD7AF),  # Hangul syllables
        (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
    )
    _CYRILLIC_RANGE = (0x0400, 0x052F)

    def validate_reply(self, *, text: str, locale: str | None) -> LocaleTextValidation:
        normalized = (text or "").strip()
        if not normalized:
            return LocaleTextValidation(False, "empty")
        if self.contains_cjk(normalized):
            return LocaleTextValidation(False, "forbidden_cjk_script")
        if self._is_english_locale(locale) and self.contains_cyrillic(normalized):
            return LocaleTextValidation(False, "unexpected_cyrillic_for_english_locale")
        return LocaleTextValidation(True)

    def contains_cjk(self, text: str) -> bool:
        return any(self._in_ranges(ord(char), self._CJK_RANGES) for char in text)

    def contains_cyrillic(self, text: str) -> bool:
        return any(self._in_range(ord(char), self._CYRILLIC_RANGE) for char in text)

    def forbidden_script_instruction(self, *, locale: str | None) -> str:
        if self._is_russian_locale(locale):
            return (
                "The user-facing final_text and cta_text must be Russian written in Cyrillic. "
                "Short canonical Latin style names are allowed, but Chinese, Japanese, and Korean scripts are forbidden."
            )
        return (
            "The user-facing final_text and cta_text must be English written in Latin script. "
            "Chinese, Japanese, Korean, and Cyrillic scripts are forbidden."
        )

    def _is_russian_locale(self, locale: str | None) -> bool:
        return (locale or "").strip().lower().startswith("ru")

    def _is_english_locale(self, locale: str | None) -> bool:
        return not self._is_russian_locale(locale)

    def _in_ranges(self, codepoint: int, ranges: tuple[tuple[int, int], ...]) -> bool:
        return any(self._in_range(codepoint, item) for item in ranges)

    def _in_range(self, codepoint: int, item: tuple[int, int]) -> bool:
        start, end = item
        return start <= codepoint <= end
