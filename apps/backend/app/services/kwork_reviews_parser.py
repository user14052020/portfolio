from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx


KWORK_ORIGIN = "https://kwork.ru"
DEFAULT_KWORK_PROFILE_URL = "https://kwork.ru/user/portfolio-dev"


@dataclass(frozen=True)
class ParsedKworkReview:
    external_id: str
    source_url: str
    source_platform: str
    review_type: str
    author_name: str
    author_url: str | None
    author_avatar_url: str | None
    project_title: str | None
    project_url: str | None
    rating: int
    text: str
    reviewed_at: datetime | None
    time_ago: str | None
    payload: dict[str, Any]
    sort_order: int
    is_published: bool

    def to_model_data(self) -> dict[str, Any]:
        return {
            "external_id": self.external_id,
            "source_url": self.source_url,
            "source_platform": self.source_platform,
            "review_type": self.review_type,
            "author_name": self.author_name,
            "author_url": self.author_url,
            "author_avatar_url": self.author_avatar_url,
            "project_title": self.project_title,
            "project_url": self.project_url,
            "rating": self.rating,
            "text": self.text,
            "reviewed_at": self.reviewed_at,
            "time_ago": self.time_ago,
            "payload": self.payload,
            "sort_order": self.sort_order,
            "is_published": self.is_published,
        }


class KworkReviewsParser:
    def __init__(self, *, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def parse_profile_reviews(
        self,
        source_url: str = DEFAULT_KWORK_PROFILE_URL,
        *,
        limit: int = 100,
    ) -> list[ParsedKworkReview]:
        profile_url = self._normalize_profile_url(source_url)
        headers = self._build_headers(profile_url)
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers=headers,
        ) as client:
            profile_response = await client.get(profile_url)
            profile_response.raise_for_status()
            profile_data = self._extract_state_data(profile_response.text)
            user_id = int(profile_data.get("userProfileId") or 0)
            if user_id <= 0:
                raise ValueError("Kwork profile user id was not found in page state")

            raw_reviews: list[dict[str, Any]] = []
            for review_type in ("positive", "negative"):
                raw_reviews.extend(
                    await self._load_reviews(
                        client,
                        user_id=user_id,
                        review_type=review_type,
                        limit=limit,
                    )
                )

        reviews = [
            self._map_review(raw_review, profile_url, index)
            for index, raw_review in enumerate(raw_reviews)
            if self._clean_text(raw_review.get("comment_source") or raw_review.get("text") or raw_review.get("comment"))
        ]
        return reviews

    async def _load_reviews(
        self,
        client: httpx.AsyncClient,
        *,
        user_id: int,
        review_type: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        response = await client.post(
            f"{KWORK_ORIGIN}/user/get_reviews",
            json={
                "userId": user_id,
                "type": review_type,
                "offset": 0,
                "limit": limit,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success"):
            raise ValueError(f"Kwork reviews endpoint returned unsuccessful response for {review_type}")
        data = payload.get("data") or {}
        reviews = data.get("reviews") or []
        return [review for review in reviews if isinstance(review, dict)]

    def _map_review(self, raw_review: dict[str, Any], source_url: str, sort_order: int) -> ParsedKworkReview:
        review_id = self._clean_text(raw_review.get("RID") or raw_review.get("ratings_for_display_id"))
        author_name = self._clean_text(
            raw_review.get("raterDisplayName") or raw_review.get("username") or "Kwork user"
        )
        kwork_data = raw_review.get("kwork") if isinstance(raw_review.get("kwork"), dict) else {}
        project_url = self._normalize_optional_url(kwork_data.get("url") if kwork_data else None)
        project_title = self._clean_text(raw_review.get("kworkTitle") or kwork_data.get("gtitle"))
        text = self._clean_text(raw_review.get("comment_source") or raw_review.get("text") or raw_review.get("comment"))
        is_positive = str(raw_review.get("good") or "1") == "1"

        return ParsedKworkReview(
            external_id=f"kwork:{review_id}" if review_id else f"kwork:{source_url}:{sort_order}",
            source_url=source_url,
            source_platform="kwork",
            review_type="positive" if is_positive else "negative",
            author_name=author_name,
            author_url=self._normalize_optional_url(raw_review.get("profile_url")),
            author_avatar_url=self._build_avatar_url(raw_review.get("profilepicture")),
            project_title=project_title or None,
            project_url=project_url,
            rating=5 if is_positive else 1,
            text=text,
            reviewed_at=self._parse_timestamp(raw_review.get("time_added")),
            time_ago=self._clean_text(raw_review.get("time_ago")) or None,
            payload=raw_review,
            sort_order=sort_order,
            is_published=True,
        )

    def _extract_state_data(self, html: str) -> dict[str, Any]:
        marker = "window.stateData="
        start = html.find(marker)
        if start < 0:
            raise ValueError("Kwork profile state data was not found")
        start += len(marker)
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(html)):
            char = html[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(html[start : index + 1])
        raise ValueError("Kwork profile state data is malformed")

    def _normalize_profile_url(self, source_url: str) -> str:
        cleaned = source_url.strip() or DEFAULT_KWORK_PROFILE_URL
        parsed = urlparse(cleaned)
        if not parsed.scheme:
            cleaned = f"https://{cleaned}"
            parsed = urlparse(cleaned)
        if parsed.netloc.lower().removeprefix("www.") != "kwork.ru":
            raise ValueError("Only kwork.ru profile URLs are supported")
        return cleaned

    def _normalize_optional_url(self, value: Any) -> str | None:
        text = self._clean_text(value)
        if not text:
            return None
        return urljoin(KWORK_ORIGIN, text)

    def _build_avatar_url(self, value: Any) -> str | None:
        path = self._clean_text(value)
        if not path or path == "noprofilepicture.gif":
            return None
        return urljoin("https://cdn-edge.kwork.ru/files/avatar/medium/", path)

    def _parse_timestamp(self, value: Any) -> datetime | None:
        try:
            timestamp = int(str(value))
        except (TypeError, ValueError):
            return None
        return datetime.fromtimestamp(timestamp, tz=UTC)

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return ""
        text = unescape(str(value))
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _build_headers(self, referer: str) -> dict[str, str]:
        return {
            "Accept": "application/json,text/plain,*/*",
            "Origin": KWORK_ORIGIN,
            "Referer": referer,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
        }


kwork_reviews_parser = KworkReviewsParser()
