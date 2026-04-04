import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.models.enums import GenerationStatus


@dataclass
class ProviderStatus:
    status: GenerationStatus
    progress: int
    image_url: str | None = None
    error_message: str | None = None
    raw_payload: dict[str, Any] | None = None


class ComfyUIClientError(RuntimeError):
    pass


class ComfyUIClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.comfyui_base_url.rstrip("/")

    async def queue_prompt(self, workflow: dict[str, Any]) -> str:
        payload = {"prompt": workflow, "client_id": self.settings.comfyui_client_id}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.base_url}/prompt", json=payload)
            if response.is_error:
                error_details = self._extract_error_details(response)
                raise ComfyUIClientError(
                    f"ComfyUI prompt submission failed with status {response.status_code}: {error_details}"
                )
            data = response.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return prompt_id")
        return str(prompt_id)

    async def get_job_status(self, prompt_id: str) -> ProviderStatus:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{self.base_url}/history/{prompt_id}")
            response.raise_for_status()
            history = response.json()

        job_data = history.get(prompt_id)
        if not job_data:
            return ProviderStatus(status=GenerationStatus.QUEUED, progress=20, raw_payload=history)

        status_block = job_data.get("status", {})
        if status_block.get("completed") is True:
            image_url = self._extract_image_url(job_data)
            return ProviderStatus(
                status=GenerationStatus.COMPLETED,
                progress=100,
                image_url=image_url,
                raw_payload=job_data,
            )

        if status_block.get("status_str") == "error":
            return ProviderStatus(
                status=GenerationStatus.FAILED,
                progress=100,
                error_message=status_block.get("messages", [{}])[-1].get("message", "Generation failed"),
                raw_payload=job_data,
            )

        return ProviderStatus(status=GenerationStatus.RUNNING, progress=65, raw_payload=job_data)

    def build_workflow(
        self,
        *,
        prompt: str,
        negative_prompt: str,
        input_image_url: str | None,
        body_height_cm: int | None,
        body_weight_kg: int | None,
    ) -> dict[str, Any]:
        template_path = Path(self.settings.comfyui_workflow_template)
        workflow = json.loads(template_path.read_text(encoding="utf-8"))
        replacements = {
            "__CHECKPOINT_NAME__": self.settings.comfyui_checkpoint_name,
            "__PROMPT__": prompt,
            "__NEGATIVE_PROMPT__": negative_prompt,
            "__INPUT_IMAGE_URL__": input_image_url or "",
            "__BODY_HEIGHT_CM__": str(body_height_cm or ""),
            "__BODY_WEIGHT_KG__": str(body_weight_kg or ""),
        }
        return self._replace_placeholders(deepcopy(workflow), replacements)

    def _replace_placeholders(self, payload: Any, replacements: dict[str, str]) -> Any:
        if isinstance(payload, str):
            result = payload
            for key, value in replacements.items():
                result = result.replace(key, value)
            return result
        if isinstance(payload, dict):
            return {key: self._replace_placeholders(value, replacements) for key, value in payload.items()}
        if isinstance(payload, list):
            return [self._replace_placeholders(item, replacements) for item in payload]
        return payload

    def _extract_image_url(self, job_data: dict[str, Any]) -> str | None:
        outputs = job_data.get("outputs", {})
        for node_output in outputs.values():
            images = node_output.get("images")
            if not images:
                continue
            image = images[0]
            filename = image.get("filename")
            subfolder = image.get("subfolder", "")
            file_type = image.get("type", "output")
            return f"{self.base_url}/view?filename={filename}&subfolder={subfolder}&type={file_type}"
        return None

    def _extract_error_details(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
            return json.dumps(payload, ensure_ascii=False)
        except ValueError:
            text = response.text.strip()
            return text or "no response body"
