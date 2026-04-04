# 07. vLLM Runtime Reference

Этот файл фиксирует, как `vLLM` устроен именно в текущем проекте и на текущем окружении.

## Назначение

`vLLM` в этом проекте отвечает только за текстовый reasoning стилиста:

- разбор пользовательского сообщения;
- текстовую рекомендацию;
- выбор route:
  - `text_only`
  - `text_and_generation`
  - `text_and_catalog`
- генерацию английского prompt для `ComfyUI`.

`vLLM` не занимается image generation. Генерация картинки остаётся в `ComfyUI`.

## Где находится

### Windows host

- project root: `C:\dev\portfolio`
- start script: `C:\dev\Scripts\start-vllm.ps1`
- logs: `C:\dev\ServiceLogs\vLLM\YYYY-MM-DD.log`

### WSL

- distro: `Ubuntu-22.04`
- Python venv: `/root/venvs/vllm`
- server process:
  `/root/venvs/vllm/bin/python -u -m vllm.entrypoints.openai.api_server`

### Network

- host local endpoint: `http://127.0.0.1:8001/v1`
- VM/backend endpoint: `http://192.168.50.141:8001/v1`

Основная проверка:

```bash
curl -fsS http://192.168.50.141:8001/v1/models
```

## Какая модель используется

Текущая рабочая модель:

- `Qwen/Qwen2.5-3B-Instruct`

Она зафиксирована:

- в startup script `C:\dev\Scripts\start-vllm.ps1`
- в backend env:
  - `VLLM_MODEL=Qwen/Qwen2.5-3B-Instruct`

## Как устанавливался

Базовый установочный сценарий для этого проекта:

1. Поднять `WSL Ubuntu-22.04` на Windows host.
2. Установить системные пакеты внутри `WSL`:
   - `python3-venv`
   - `python3-pip`
   - `git`
3. Создать venv:
   - `/root/venvs/vllm`
4. Установить `vllm` внутрь этого venv.
5. Запустить `OpenAI-compatible server` на порту `8001`.

Полный пошаговый процесс лежит в:

- [02-vllm-on-win11-host.md](./02-vllm-on-win11-host.md)

Этот файл не заменяет `02`, а фиксирует текущее состояние после установки.

## Текущая команда запуска

Сейчас рабочий runtime запускается так:

```powershell
wsl.exe -d Ubuntu-22.04 -- sh -lc "export HF_HUB_DISABLE_XET=1; exec /root/venvs/vllm/bin/python -u -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-3B-Instruct --host 0.0.0.0 --port 8001 --max-model-len 2048 --enforce-eager"
```

Ключевые параметры:

- `--host 0.0.0.0`
- `--port 8001`
- `--max-model-len 2048`
- `--enforce-eager`

## Где используется в коде проекта

Backend использует `vLLM` через:

- `apps/backend/app/integrations/vllm.py`
- `apps/backend/app/services/stylist_prompt_policy.py`
- `apps/backend/app/services/stylist_ai.py`

Backend env:

- `VLLM_BASE_URL`
- `VLLM_MODEL`
- `VLLM_API_KEY`
- `VLLM_TIMEOUT_SECONDS`
- `VLLM_TEMPERATURE`
- `VLLM_MAX_TOKENS`

## Автозапуск

`vLLM` стартует на Windows host через:

- `Task Scheduler`
- script: `C:\dev\Scripts\start-vllm.ps1`

Рекомендуемая задача:

- task name: `vLLM-WSL`
- trigger: `At startup`
- run with highest privileges
- account: обычный Windows user, не `SYSTEM`

Важно:

- `wsl.exe` не должен запускаться из-под `SYSTEM`
- иначе возникает `WSL_E_LOCAL_SYSTEM_NOT_SUPPORTED`

Подробности по автозапуску:

- [06-autostart-map.md](./06-autostart-map.md)

## Известные особенности

### WSL localhost warning в логах

В логах `start-vllm.ps1` может появляться предупреждение `WSL` про `localhost` и `NAT`.

Для текущего проекта это не считается блокирующей ошибкой, если одновременно выполняются проверки:

```powershell
curl.exe http://127.0.0.1:8001/v1/models
```

и

```bash
curl -fsS http://192.168.50.141:8001/v1/models
```

То есть warning сам по себе допустим, если endpoint реально отвечает.

### Язык ответа модели

Backend дополнительно валидирует ответ `vLLM`, чтобы:

- `reply_ru` был на русском;
- `reply_en` был на английском;
- primary-ответ не содержал смешанных языков или `CJK`-символов.

Если `vLLM` отдаёт некорректный ответ, backend уходит в безопасный fallback.

## Что проверять после изменений

После любых изменений в runtime или config:

```bash
curl -fsS http://192.168.50.141:8001/v1/models
```

и затем из backend:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/stylist-chat/message \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "manual-vllm-test-1",
    "locale": "ru",
    "message": "У меня черный пиджак, хочу образ с легкой иронией в тоне ответа. Что добавить?",
    "auto_generate": false
  }'
```
