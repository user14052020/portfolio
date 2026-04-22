import json
import secrets
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.application.visual_generation.contracts import PreparedGenerationRun
from app.core.config import get_settings
from app.domain.visual_generation import VisualGenerationPlan
from app.models.enums import GenerationStatus


@dataclass
class ProviderStatus:
    status: GenerationStatus
    progress: int
    image_url: str | None = None
    error_message: str | None = None
    raw_payload: dict[str, Any] | None = None
    in_queue_pending: bool = False
    in_queue_running: bool = False


class ComfyClientError(RuntimeError):
    pass


class ComfyClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.comfyui_base_url.rstrip("/")

    async def prepare_run(
        self,
        *,
        plan: VisualGenerationPlan,
        input_image_url: str | None,
        body_height_cm: int | None,
        body_weight_kg: int | None,
    ) -> PreparedGenerationRun:
        workflow_path = Path(plan.workflow_version or "")
        if not workflow_path.exists():
            workflow_path = Path("app/infrastructure/comfy/workflows") / (plan.workflow_name + ".json")
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        seed = self._generate_seed()
        replacements: dict[str, Any] = {
            "__DIFFUSION_MODEL_NAME__": self.settings.comfyui_diffusion_model_name,
            "__TEXT_ENCODER_T5_NAME__": self.settings.comfyui_text_encoder_t5_name,
            "__TEXT_ENCODER_CLIP_L_NAME__": self.settings.comfyui_text_encoder_clip_l_name,
            "__VAE_NAME__": self.settings.comfyui_vae_name,
            "__SEED__": seed,
            "__PROMPT__": plan.final_prompt,
            "__NEGATIVE_PROMPT__": plan.negative_prompt or "",
            "__INPUT_IMAGE_URL__": input_image_url or "",
            "__BODY_HEIGHT_CM__": str(body_height_cm or ""),
            "__BODY_WEIGHT_KG__": str(body_weight_kg or ""),
        }
        return PreparedGenerationRun(
            workflow_payload=self._replace_placeholders(deepcopy(workflow), replacements),
            seed=seed,
            workflow_name=plan.workflow_name,
            workflow_version=workflow_path.name,
        )

    async def submit(self, *, workflow_payload: dict[str, Any]) -> str:
        payload = {"prompt": workflow_payload, "client_id": self.settings.comfyui_client_id}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.base_url}/prompt", json=payload)
            if response.is_error:
                raise ComfyClientError(
                    f"ComfyUI prompt submission failed with status {response.status_code}: {self._extract_error_details(response)}"
                )
            data = response.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return prompt_id")
        return str(prompt_id)

    async def get_job_status(self, prompt_id: str) -> ProviderStatus:
        async with httpx.AsyncClient(timeout=15.0) as client:
            history_response = await client.get(f"{self.base_url}/history/{prompt_id}")
            history_response.raise_for_status()
            history = history_response.json()
            queue_response = await client.get(f"{self.base_url}/queue")
            queue_response.raise_for_status()
            queue_payload = queue_response.json()

        job_data = history.get(prompt_id)
        in_queue_pending = self._queue_contains_prompt(queue_payload, "queue_pending", prompt_id)
        in_queue_running = self._queue_contains_prompt(queue_payload, "queue_running", prompt_id)
        raw_payload = {"history": history, "queue": queue_payload}

        if not job_data:
            if in_queue_running:
                return ProviderStatus(status=GenerationStatus.RUNNING, progress=65, raw_payload=raw_payload, in_queue_running=True)
            if in_queue_pending:
                return ProviderStatus(status=GenerationStatus.QUEUED, progress=20, raw_payload=raw_payload, in_queue_pending=True)
            return ProviderStatus(
                status=GenerationStatus.FAILED,
                progress=100,
                error_message="ComfyUI lost the prompt before completion. Check the ComfyUI runtime log.",
                raw_payload=raw_payload,
            )

        status_block = job_data.get("status", {})
        if status_block.get("completed") is True:
            return ProviderStatus(
                status=GenerationStatus.COMPLETED,
                progress=100,
                image_url=self._extract_image_url(job_data),
                raw_payload=raw_payload,
                in_queue_pending=in_queue_pending,
                in_queue_running=in_queue_running,
            )
        if status_block.get("status_str") == "error":
            return ProviderStatus(
                status=GenerationStatus.FAILED,
                progress=100,
                error_message=status_block.get("messages", [{}])[-1].get("message", "Generation failed"),
                raw_payload=raw_payload,
                in_queue_pending=in_queue_pending,
                in_queue_running=in_queue_running,
            )
        return ProviderStatus(
            status=GenerationStatus.RUNNING,
            progress=65,
            raw_payload=raw_payload,
            in_queue_pending=in_queue_pending,
            in_queue_running=in_queue_running,
        )

    async def delete_queued_prompt(self, prompt_id: str) -> None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{self.base_url}/queue", json={"delete": [prompt_id]})
            if response.is_error:
                raise ComfyClientError(
                    f"ComfyUI queue delete failed with status {response.status_code}: {self._extract_error_details(response)}"
                )

    async def interrupt_current_prompt(self) -> None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{self.base_url}/interrupt", json={})
            if response.is_error:
                raise ComfyClientError(
                    f"ComfyUI interrupt failed with status {response.status_code}: {self._extract_error_details(response)}"
                )

    def _replace_placeholders(self, payload: Any, replacements: dict[str, Any]) -> Any:
        if isinstance(payload, str):
            if payload in replacements:
                return replacements[payload]
            result = payload
            for key, value in replacements.items():
                result = result.replace(key, str(value))
            return result
        if isinstance(payload, dict):
            return {key: self._replace_placeholders(value, replacements) for key, value in payload.items()}
        if isinstance(payload, list):
            return [self._replace_placeholders(item, replacements) for item in payload]
        return payload

    def _generate_seed(self) -> int:
        return secrets.randbelow(2**63 - 1) + 1

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
            return (
                "/api/v1/generation-jobs/image-proxy"
                f"?filename={filename}&subfolder={subfolder}&type={file_type}"
            )
        return None

    def _queue_contains_prompt(self, queue_payload: dict[str, Any], section: str, prompt_id: str) -> bool:
        return self._payload_contains_prompt_id(queue_payload.get(section, []), prompt_id)

    def _payload_contains_prompt_id(self, payload: Any, prompt_id: str) -> bool:
        if isinstance(payload, str):
            return payload == prompt_id
        if isinstance(payload, dict):
            return any(self._payload_contains_prompt_id(value, prompt_id) for value in payload.values())
        if isinstance(payload, list):
            return any(self._payload_contains_prompt_id(item, prompt_id) for item in payload)
        return False

    def _extract_error_details(self, response: httpx.Response) -> str:
        try:
            return json.dumps(response.json(), ensure_ascii=False)
        except ValueError:
            return response.text.strip() or "no response body"

