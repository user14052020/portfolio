from pydantic import BaseModel, Field

from .style_direction import StyleDirection


class StyleHistory(BaseModel):
    directions: list[StyleDirection] = Field(default_factory=list)
    limit: int = 5

    def recent(self) -> list[StyleDirection]:
        return self.directions[-self.limit :]

    def remember(self, style_direction: StyleDirection) -> None:
        retained: list[StyleDirection] = []
        next_key = style_direction.key()
        for existing in self.directions:
            existing_key = existing.key()
            if next_key and existing_key and next_key == existing_key:
                continue
            retained.append(existing)
        retained.append(style_direction)
        self.directions = retained[-self.limit :]
