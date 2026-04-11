# Установка и автозапуск vLLM на Windows 11 Pro через WSL2

## Целевая схема

Рекомендуемая production-like схема для локального сервиса vLLM:

- Windows 11 Pro
- WSL2 с Ubuntu
- vLLM запускается **внутри Ubuntu**
- `systemd` управляет жизненным циклом `vLLM`
- Windows только “будит” WSL при логине и запускает `systemctl start vllm.service`

Такой вариант стабильнее, чем:
- толстый PowerShell-скрипт с логикой запуска/остановки
- длинные задачи в Планировщике
- ручной запуск в терминале

---

# 1. Установить WSL2 и Ubuntu

Открой **PowerShell от имени администратора** и выполни:

```powershell
wsl --install -d Ubuntu-22.04
```

Если WSL уже установлен, проверь список дистрибутивов:

```powershell
wsl -l -v
```

Если Ubuntu установлена, но не WSL2, переведи её в WSL2:

```powershell
wsl --set-version Ubuntu-22.04 2
```

Проверь версию WSL:

```powershell
wsl --version
```

---

# 2. Зайти в Ubuntu и обновить систему

```powershell
wsl -d Ubuntu-22.04
```

Внутри Ubuntu:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip curl git
```

---

# 3. Проверить доступ к GPU в WSL

В Ubuntu:

```bash
nvidia-smi
```

Если команда показывает RTX 3090, значит GPU в WSL виден корректно.

---

# 4. Создать отдельное Python-окружение для vLLM

В Ubuntu:

```bash
mkdir -p /home/dev/venvs
python3 -m venv /home/dev/venvs/vllm
source /home/dev/venvs/vllm/bin/activate
python -m pip install -U pip setuptools wheel
```

---

# 5. Установить vLLM

В активированном окружении:

```bash
pip install vllm huggingface_hub
```

Проверка:

```bash
python -m vllm.entrypoints.openai.api_server --help
```

---

# 6. Скачать модель локально

Создай папку под модели:

```bash
mkdir -p /home/dev/models/Qwen2.5-3B-Instruct
```

Скачай модель в локальную папку:

```bash
python3 -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Qwen/Qwen2.5-3B-Instruct', local_dir='/home/dev/models/Qwen2.5-3B-Instruct', local_dir_use_symlinks=False)"
```

Проверь, что файлы на месте:

```bash
ls -lah /home/dev/models/Qwen2.5-3B-Instruct
```

Там должны быть как минимум:
- `config.json`
- `generation_config.json`
- tokenizer-файлы
- `model-00001-of-*.safetensors`
- `model-00002-of-*.safetensors`

---

# 7. Включить systemd в WSL

Открой файл:

```bash
sudo nano /etc/wsl.conf
```

Вставь:

```ini
[boot]
systemd=true
```

Сохрани файл.

Теперь на Windows:

```powershell
wsl --shutdown
```

Снова зайди в Ubuntu:

```powershell
wsl -d Ubuntu-22.04
```

Проверь, что `systemd` работает:

```bash
systemctl is-system-running
```

---

# 8. Создать папку под логи vLLM

В Ubuntu:

```bash
mkdir -p /home/dev/logs/vllm
```

---

# 9. Создать systemd service для vLLM

Открой unit-файл:

```bash
sudo nano /etc/systemd/system/vllm.service
```

Вставь:

```ini
[Unit]
Description=vLLM OpenAI API Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=dev
WorkingDirectory=/home/dev
Environment=HF_HUB_DISABLE_XET=1
Environment=HF_HUB_OFFLINE=1
Environment=TRANSFORMERS_OFFLINE=1
ExecStart=/home/dev/venvs/vllm/bin/python -u -m vllm.entrypoints.openai.api_server --model /home/dev/models/Qwen2.5-3B-Instruct --served-model-name Qwen/Qwen2.5-3B-Instruct --host 0.0.0.0 --port 8001 --max-model-len 4096 --enforce-eager --gpu-memory-utilization 0.6
Restart=always
RestartSec=5
TimeoutStartSec=600
StandardOutput=append:/home/dev/logs/vllm/stdout.log
StandardError=append:/home/dev/logs/vllm/stderr.log

[Install]
WantedBy=multi-user.target
```

Сохрани файл.

---

# 10. Подхватить и включить сервис

В Ubuntu:

```bash
sudo systemctl daemon-reload
sudo systemctl enable vllm.service
sudo systemctl start vllm.service
```

Проверить статус:

```bash
sudo systemctl status vllm.service --no-pager
```

Смотреть логи:

```bash
journalctl -u vllm.service -f
```

Или:

```bash
tail -f /home/dev/logs/vllm/stdout.log
tail -f /home/dev/logs/vllm/stderr.log
```

---

# 11. Проверить API внутри WSL

В Ubuntu:

```bash
curl http://127.0.0.1:8001/v1/models
```

Ожидается JSON со списком моделей.

---

# 12. Проверить API с Windows-хоста

В PowerShell:

```powershell
curl http://127.0.0.1:8001/v1/models
```

Если `localhost` в твоём сетапе не работает, используй IP хоста из WSL mirrored networking, например:

```powershell
curl http://192.168.50.141:8001/v1/models
```

Если backend проекта использует внешний адрес, пропиши его в `.env`, например:

```env
VLLM_BASE_URL=http://192.168.50.141:8001/v1
VLLM_MODEL=Qwen/Qwen2.5-3B-Instruct
VLLM_MAX_MODEL_LEN=4096
```

---

# 13. Сделать автозапуск при логине Windows

Сам `vllm.service` живёт внутри Ubuntu, но WSL нужно разбудить после входа в Windows.

Создай файл:

```text
C:\dev\scripts\wake-vllm-wsl.ps1
```

Содержимое:

```powershell
wsl -d Ubuntu-22.04 -- systemctl start vllm.service
```

---

# 14. Добавить bootstrap в Планировщик задач

Создай новую задачу в **Task Scheduler**:

## General
- Name: `Wake WSL vLLM`
- Run whether user is logged on or not — по желанию
- Run with highest privileges — можно включить

## Trigger
- `At log on`

## Action
**Program/script:**
```text
powershell.exe
```

**Add arguments:**
```text
-NoProfile -ExecutionPolicy Bypass -File "C:\dev\scripts\wake-vllm-wsl.ps1"
```

**Start in:**
```text
C:\dev\scripts
```

---

# 15. Команды управления дальше

## Из Ubuntu

Запуск:
```bash
sudo systemctl start vllm.service
```

Остановка:
```bash
sudo systemctl stop vllm.service
```

Рестарт:
```bash
sudo systemctl restart vllm.service
```

Статус:
```bash
sudo systemctl status vllm.service --no-pager
```

Логи:
```bash
journalctl -u vllm.service -f
```

## Из Windows PowerShell

Запуск:
```powershell
wsl -d Ubuntu-22.04 -- systemctl start vllm.service
```

Остановка:
```powershell
wsl -d Ubuntu-22.04 -- systemctl stop vllm.service
```

Рестарт:
```powershell
wsl -d Ubuntu-22.04 -- systemctl restart vllm.service
```

Статус:
```powershell
wsl -d Ubuntu-22.04 -- systemctl status vllm.service --no-pager
```

---

# 16. Что важно оставить именно так

## Модель
В `vllm.service`:
- `--model` должен указывать на **локальную папку**
- `--served-model-name` должен оставаться **красивым API-именем**

То есть:
- локально грузим из `/home/dev/models/...`
- наружу backend обращается к `Qwen/Qwen2.5-3B-Instruct`

## Почему это правильно
Так:
- старт не зависит от Hugging Face
- backend не ломается
- документация остаётся чистой
- API-контракт стабильный

---

# 17. Короткий чек-лист готовности

Система настроена правильно, если:

- `wsl --version` работает
- `systemd` включён в `/etc/wsl.conf`
- `nvidia-smi` внутри WSL видит GPU
- `vllm.service` запускается через `systemctl`
- `curl http://127.0.0.1:8001/v1/models` внутри WSL отвечает
- `curl http://192.168.x.x:8001/v1/models` с Windows отвечает
- при логине Windows срабатывает `wake-vllm-wsl.ps1`
- backend проекта обращается к `VLLM_BASE_URL`
