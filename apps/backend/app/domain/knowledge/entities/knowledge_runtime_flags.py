from pydantic import BaseModel

from app.domain.knowledge.entities.knowledge_provider_config import KnowledgeProviderConfig


class KnowledgeRuntimeFlags(BaseModel):
    style_ingestion_enabled: bool = True
    malevich_enabled: bool = False
    fashion_historian_enabled: bool = False
    stylist_enabled: bool = False
    use_editorial_knowledge: bool = False
    use_historical_context: bool = True
    use_color_poetics: bool = True

    def allows_provider(self, config: KnowledgeProviderConfig) -> bool:
        code = config.code.strip().lower()
        roles = {role.strip().lower() for role in config.runtime_roles if isinstance(role, str) and role.strip()}

        if code == "style_ingestion" and not self.style_ingestion_enabled:
            return False
        if code == "malevich" and (not self.malevich_enabled or not self.use_color_poetics):
            return False
        if code == "fashion_historian" and (
            not self.fashion_historian_enabled or not self.use_historical_context
        ):
            return False
        if code in {"stylist", "stylist_editorial"} and (
            not self.stylist_enabled or not self.use_editorial_knowledge
        ):
            return False
        if "editorial" in roles and not self.use_editorial_knowledge:
            return False
        if "historical_context" in roles and not self.use_historical_context:
            return False
        if "color_poetics" in roles and not self.use_color_poetics:
            return False
        return True
