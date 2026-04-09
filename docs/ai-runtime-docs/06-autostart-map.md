# 06. Autostart Map

Этот файл фиксирует, что именно должно лежать в автозапуске, где находятся проект и сервисы, и как хранить логи.

## Пути

- Windows host project: `C:\dev\portfolio`
- Windows host ComfyUI: `C:\dev\ComfyUI`
- Windows host scripts: `C:\dev\Scripts`
- Ubuntu VM project: `/home/webh/projects/portfolio`

## Что должно запускаться автоматически

### Ubuntu VM

После перезагрузки Ubuntu VM должны автоматически стартовать:

- `docker.service`
- `containerd.service`
- `portfolio-compose.service`

`portfolio-compose.service` должен запускать:

- `docker compose up -d`

в каталоге:

- `/home/webh/projects/portfolio`

Пример unit-файла:

```ini
[Unit]
Description=Portfolio Docker Compose Stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=webh
WorkingDirectory=/home/webh/projects/portfolio
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Проверки:

```bash
systemctl is-enabled docker.service containerd.service portfolio-compose.service
journalctl -u portfolio-compose.service --since today --no-pager
docker compose -f /home/webh/projects/portfolio/docker-compose.yml ps
```

## Логи Ubuntu VM

### systemd journal

Нужно хранить системные логи 7 дней:

```ini
[Journal]
MaxRetentionSec=7day
SystemMaxUse=1G
```

Файл:

- `/etc/systemd/journald.conf.d/retention.conf`

Проверка:

```bash
journalctl -u portfolio-compose.service --since "7 days ago" --no-pager
```

### Docker container logs

Для контейнеров использовать ротацию:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "7"
  }
}
```

Файл:

- `/etc/docker/daemon.json`

## Windows host

После перезагрузки Windows host должны автоматически стартовать:

- `ComfyUI`
- `vLLM`

Для обоих сервисов лучше использовать:

- `Task Scheduler`
- отдельные стартовые скрипты
- дневные log-файлы
- удаление логов старше 7 дней

## ComfyUI

Текущий путь:

- `C:\dev\ComfyUI`

Рекомендуемый стартовый скрипт:

- `C:\dev\Scripts\start_comfyui.bat`

Важно:

- после переноса из `C:\ComfyUI` в `C:\dev\ComfyUI` старый `activate.bat` внутри `venv` может указывать на старый путь;
- в таком случае Task Scheduler запускает системный Python вместо `venv`, и ComfyUI падает с ошибкой `Torch not compiled with CUDA enabled`.

Симптом из лога:

- `Python executable: C:\Program Files\Python310\python.exe`

Это означает, что был взят не `C:\dev\ComfyUI\venv\Scripts\python.exe`.

Надёжнее запускать ComfyUI напрямую через python из `venv`, без `activate.bat`.

Рекомендуемый вариант `start-comfyui.cmd`:

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

Task Scheduler:

- task name: `ComfyUI`
- trigger: `At startup`
- run with highest privileges

## vLLM

`vLLM` работает на Windows host через `WSL Ubuntu-22.04`.

Текущий рабочий запуск:

```powershell
wsl -d Ubuntu-22.04 -- sh -lc "export HF_HUB_DISABLE_XET=1; exec /root/venvs/vllm/bin/python -u -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-3B-Instruct --host 0.0.0.0 --port 8001 --max-model-len 2048 --enforce-eager"
```

Рекомендуемый стартовый скрипт:

- `C:\dev\Scripts\start-vllm.ps1`

Логи:

- `C:\dev\ServiceLogs\vLLM\YYYY-MM-DD.log`

Task Scheduler:

- task name: `vLLM-WSL`
- trigger: `At startup`
- run with highest privileges

## Сетевой доступ с Ubuntu VM

Для Ubuntu VM сейчас используются host endpoints:

- `ComfyUI`: `http://192.168.50.141:8188`
- `vLLM`: `http://192.168.50.141:8001/v1`

Проверки из Ubuntu VM:

```bash
curl -fsS http://192.168.50.141:8001/v1/models
curl -fsS http://192.168.50.141:8188/ > /dev/null && echo COMFYUI_OK
```
