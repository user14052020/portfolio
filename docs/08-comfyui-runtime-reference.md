# 08. ComfyUI Runtime Reference

Этот файл фиксирует, как `ComfyUI` устроен именно в текущем проекте и на текущем окружении.

## Назначение

`ComfyUI` в этом проекте отвечает только за генерацию изображений.

Он получает от backend:

- английский `prompt`;
- negative prompt;
- при необходимости входной image reference;
- body hints, если они есть.

`ComfyUI` не занимается reasoning и не формирует текстовую рекомендацию. Это зона `vLLM`.

## Где находится

### Windows host

- project root: `C:\dev\portfolio`
- ComfyUI root: `C:\dev\ComfyUI`
- Python venv: `C:\dev\ComfyUI\venv`
- start script: `C:\dev\Scripts\start_comfyui.bat`
- logs: `C:\dev\ServiceLogs\ComfyUI\YYYY-MM-DD.log`

### Network

- host local endpoint: `http://127.0.0.1:8188`
- host LAN endpoint: `http://192.168.50.141:8188`

Проверки:

```powershell
curl.exe http://127.0.0.1:8188/
curl.exe http://192.168.50.141:8188/
```

и из Ubuntu VM:

```bash
curl -I http://192.168.50.141:8188
```

## Как используется в проекте

Backend интеграция:

- `apps/backend/app/integrations/comfyui.py`
- `apps/backend/app/services/generation.py`

Backend env:

- `COMFYUI_BASE_URL`
- `COMFYUI_CLIENT_ID`
- `COMFYUI_CHECKPOINT_NAME`
- `COMFYUI_WORKFLOW_TEMPLATE`

Workflow template:

- `apps/backend/app/integrations/workflows/fashion_flatlay.json`

Current checkpoint configured for this project:

- `COMFYUI_CHECKPOINT_NAME=v1-5-pruned-emaonly.safetensors`

## Как устанавливался и где лежит после установки

Текущая рабочая установка находится по пути:

- `C:\dev\ComfyUI`

Важно:

- раньше `ComfyUI` лежал в `C:\ComfyUI`
- после переноса в `C:\dev\ComfyUI` нельзя надёжно полагаться на старый `activate.bat` внутри `venv`

Причина:

- после переезда `activate.bat` может содержать старые абсолютные пути
- тогда `Task Scheduler` поднимает системный Python вместо `C:\dev\ComfyUI\venv\Scripts\python.exe`
- в результате `ComfyUI` падает с `Torch not compiled with CUDA enabled`

Поэтому для этого проекта правильный запуск:

- напрямую через `C:\dev\ComfyUI\venv\Scripts\python.exe`
- без `activate.bat`

## Текущая команда запуска

Текущий рабочий startup script:

```bat
@echo off
setlocal

set LOGDIR=C:\dev\ServiceLogs\ComfyUI
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set LOGDATE=%%I
powershell -NoProfile -Command "Get-ChildItem '%LOGDIR%' -Filter '*.log' -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item -Force"

echo [%date% %time%] START >> "%LOGDIR%\%LOGDATE%.log"

cd /d C:\dev\ComfyUI
C:\dev\ComfyUI\venv\Scripts\python.exe C:\dev\ComfyUI\main.py --listen 0.0.0.0 --port 8188 >> "%LOGDIR%\%LOGDATE%.log" 2>&1

set EXITCODE=%ERRORLEVEL%
echo [%date% %time%] STOP exit=%EXITCODE% >> "%LOGDIR%\%LOGDATE%.log"
exit /b %EXITCODE%
```

Ключевой момент:

- `ComfyUI` слушает сразу `0.0.0.0:8188`

То есть для него больше не нужен `portproxy`, как раньше.

## Автозапуск

`ComfyUI` стартует на Windows host через:

- `Task Scheduler`
- script: `C:\dev\Scripts\start_comfyui.bat`

Рекомендуемая задача:

- task name: `ComfyUI`
- trigger: `At startup`
- run with highest privileges

Подробности по автозапуску:

- [06-autostart-map.md](./06-autostart-map.md)

## Сетевой доступ

Сейчас ожидаемая схема такая:

- `ComfyUI` сам слушает `0.0.0.0:8188`
- firewall открывает `8188`
- `portproxy` для `ComfyUI` не нужен

Рабочий endpoint для Ubuntu VM и backend container:

- `http://192.168.50.141:8188`

## Известные особенности

### 400 Bad Request на `/prompt`

Историческая причина ошибки `400` в этом проекте была такой:

- в workflow был зашит placeholder checkpoint:
  `replace-with-your-fashion-model.safetensors`
- текущий `ComfyUI` его не знал
- из-за этого `POST /prompt` валился на валидации workflow

Теперь это вынесено в env:

- `COMFYUI_CHECKPOINT_NAME`

Если ошибка повторится, первым делом проверять:

- существует ли checkpoint из env в установленном `ComfyUI`;
- совпадает ли `COMFYUI_CHECKPOINT_NAME` со списком доступных моделей;
- какой точный body вернул `ComfyUI`.

То есть теперь причина `400` должна быть видна существенно точнее, чем раньше.

### Что считать нормальным стартом

Нормальный старт `ComfyUI`:

- локально открывается `http://127.0.0.1:8188/`
- по сети открывается `http://192.168.50.141:8188/`
- в логах нет ошибки bind на `8188`
- используется `C:\dev\ComfyUI\venv\Scripts\python.exe`

## Что проверять после изменений

После любых изменений в `ComfyUI` runtime:

```powershell
curl.exe http://127.0.0.1:8188/
curl.exe http://192.168.50.141:8188/
```

и затем из Ubuntu VM:

```bash
docker compose exec backend curl -fsS http://192.168.50.141:8188/ > /dev/null && echo COMFYUI_OK
```
