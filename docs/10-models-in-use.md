# 10. Models In Use

Этот файл фиксирует, какие модели сейчас используются в проекте для текста и генерации изображений.

## vLLM

Текстовый ассистент работает через `vLLM OpenAI-compatible server`.

Текущая модель:

- `Qwen/Qwen2.5-3B-Instruct`

Где используется:

- `apps/backend/app/integrations/vllm.py`
- `apps/backend/app/services/stylist_ai.py`

Какая env-переменная отвечает:

- `VLLM_MODEL`

Текущее значение:

```env
VLLM_MODEL=Qwen/Qwen2.5-3B-Instruct
```

Назначение:

- понимает сообщение пользователя;
- формирует текстовую рекомендацию;
- определяет routing между text-only и text-plus-generation;
- готовит английское stylist direction для генерации изображения.

## ComfyUI

Генерация изображений работает через `ComfyUI`.

Текущий стек моделей:

- diffusion model: `flux1-krea-dev_fp8_scaled.safetensors`
- text encoder T5: `t5xxl_fp8_e4m3fn.safetensors`
- text encoder CLIP-L: `clip_l.safetensors`
- VAE: `ae.safetensors`

Где лежат на Windows host:

- `C:\dev\ComfyUI\models\diffusion_models\flux1-krea-dev_fp8_scaled.safetensors`
- `C:\dev\ComfyUI\models\text_encoders\t5xxl_fp8_e4m3fn.safetensors`
- `C:\dev\ComfyUI\models\text_encoders\clip_l.safetensors`
- `C:\dev\ComfyUI\models\vae\ae.safetensors`

Какие env-переменные отвечают:

- `COMFYUI_DIFFUSION_MODEL_NAME`
- `COMFYUI_TEXT_ENCODER_T5_NAME`
- `COMFYUI_TEXT_ENCODER_CLIP_L_NAME`
- `COMFYUI_VAE_NAME`
- `COMFYUI_WORKFLOW_TEMPLATE`

Текущие значения:

```env
COMFYUI_DIFFUSION_MODEL_NAME=flux1-krea-dev_fp8_scaled.safetensors
COMFYUI_TEXT_ENCODER_T5_NAME=t5xxl_fp8_e4m3fn.safetensors
COMFYUI_TEXT_ENCODER_CLIP_L_NAME=clip_l.safetensors
COMFYUI_VAE_NAME=ae.safetensors
COMFYUI_WORKFLOW_TEMPLATE=app/integrations/workflows/fashion_flatlay.json
```

Где используется:

- `apps/backend/app/integrations/comfyui.py`
- `apps/backend/app/integrations/workflows/fashion_flatlay.json`
- `apps/backend/app/services/generation.py`

Назначение:

- генерирует glossy editorial flat lay;
- не строит сцену с человеком или манекеном;
- использует `FLUX.1 Krea dev` как основной image model stack.

## Почему выбран именно этот stack

Для текущего проекта выбран `FLUX.1 Krea dev`, потому что он лучше подходит под:

- flat lay и editorial styling;
- более эстетичную и менее synthetic картинку;
- Pinterest-like glossy visual direction.

Для `RTX 3090 24 GB` выбран `fp8_scaled` вариант, чтобы уменьшить риск по VRAM и сохранить рабочий локальный runtime.

## Следующий апгрейд

Если позже захотим поднимать качество дальше, есть два естественных шага:

1. Перейти с `flux1-krea-dev_fp8_scaled.safetensors` на полный `flux1-krea-dev.safetensors`.
2. Добавить отдельный workflow для image edit или reference-based generation, если будем сильнее опираться на пользовательские фотографии вещей.
