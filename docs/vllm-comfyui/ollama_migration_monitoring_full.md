# Переход на Ollama и настройка мониторинга

## Общая схема

В проекте выполнен переход с vLLM на Ollama.

Мониторинг и восстановление реализованы в 2 слоя:

1. WSL-уровень:
   - Ollama запущен как systemd-сервис;
   - настроен restart policy;
   - настроен systemd watchdog timer, который проверяет API Ollama и перезапускает сервис при сбое.

2. Windows-уровень:
   - используется PowerShell-скрипт `monitor.ps1`;
   - скрипт запускается через Планировщик заданий Windows;
   - скрипт проверяет доступность Ollama API;
   - при сбое перезапускает WSL и поднимает Ollama.

---

## 1. Переход с vLLM на Ollama

Ранее backend обращался к vLLM:

```env
VLLM_BASE_URL=http://<host>:8001/v1
VLLM_MODEL=Qwen/Qwen2.5-3B-Instruct
```

Теперь backend обращается к Ollama OpenAI-compatible API:

```env
VLLM_BASE_URL=http://192.168.50.141:11434/v1
VLLM_MODEL=qwen2.5:7b-instruct
```

Переменные `VLLM_*` сохранены для совместимости с существующим кодом проекта, но фактически теперь используется Ollama.

---

## 2. WSL healthcheck

В WSL создан healthcheck-скрипт:

```bash
mkdir -p ~/scripts
nano ~/scripts/ollama-health.sh
```

Содержимое:

```bash
#!/usr/bin/env bash
set -e

URL="http://127.0.0.1:11434/api/tags"

if ! curl -fsS --max-time 5 "$URL" >/dev/null; then
  echo "$(date): Ollama API failed, restarting..."
  sudo systemctl restart ollama
  exit 1
fi

echo "$(date): Ollama OK"
```

Права:

```bash
chmod +x ~/scripts/ollama-health.sh
```

---

## 3. Настройка restart policy Ollama

Открыть override systemd-сервиса:

```bash
sudo systemctl edit ollama
```

Добавить:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_KEEP_ALIVE=30s"
Restart=always
RestartSec=5
```

Применить:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

---

## 4. systemd watchdog timer в WSL

Создан service:

```bash
sudo tee /etc/systemd/system/ollama-watchdog.service > /dev/null <<'EOF'
[Unit]
Description=Ollama healthcheck watchdog

[Service]
Type=oneshot
ExecStart=/home/dev/scripts/ollama-health.sh
EOF
```

Создан timer:

```bash
sudo tee /etc/systemd/system/ollama-watchdog.timer > /dev/null <<'EOF'
[Unit]
Description=Run Ollama watchdog every 30 seconds

[Timer]
OnBootSec=30
OnUnitActiveSec=30
Unit=ollama-watchdog.service

[Install]
WantedBy=timers.target
EOF
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ollama-watchdog.timer
```

Проверка:

```bash
systemctl status ollama-watchdog.timer
systemctl list-timers | grep ollama
```

---

## 5. Windows watchdog через monitor.ps1

Для контроля WSL/Ollama на стороне Windows используется скрипт:

```text
C:\dev\projects\portfolio-src\Scripts\monitor.ps1
```

Содержимое скрипта:

```powershell
while ($true) {
    try {
        Invoke-WebRequest "http://192.168.50.141:11434/api/tags" -TimeoutSec 2 -UseBasicParsing | Out-Null
        Write-Host "$(Get-Date) OK"
    } catch {
        Write-Host "$(Get-Date) Restarting WSL..."
        wsl --shutdown
        Start-Sleep -Seconds 3
        wsl -d Ubuntu-22.04 -- bash -lc "systemctl start ollama"
    }

    Start-Sleep -Seconds 30
}
```

Назначение скрипта:

- каждые 30 секунд проверяет доступность Ollama API;
- если API отвечает — пишет `OK`;
- если API не отвечает — выполняет:
  - `wsl --shutdown`;
  - паузу 3 секунды;
  - запуск Ubuntu WSL;
  - запуск сервиса Ollama внутри WSL.

---

## 6. Запуск monitor.ps1 через Планировщик заданий Windows

Скрипт должен запускаться через Планировщик заданий Windows.

Параметры действия:

Program/script:

```text
powershell.exe
```

Arguments:

```text
-NoProfile -ExecutionPolicy Bypass -File "C:\dev\projects\portfolio-src\Scripts\monitor.ps1"
```

Start in:

```text
C:\dev\projects\portfolio-src\Scripts
```

Рекомендуемые настройки задачи:

- запускать при старте системы;
- запускать с повышенными правами;
- выполнять независимо от входа пользователя, если требуется фоновая работа;
- не завершать задачу автоматически по таймауту;
- при сбое разрешить повторный запуск.

---

## 7. Проверка работоспособности

Проверка из WSL:

```bash
curl http://127.0.0.1:11434/api/tags
systemctl status ollama
systemctl list-timers | grep ollama
```

Проверка с Windows/VM:

```powershell
curl http://192.168.50.141:11434/api/tags
```

Проверка OpenAI-compatible API:

```powershell
curl http://192.168.50.141:11434/v1/models
```

---

## 8. Контроль GPU

Для проверки использования GPU:

```bash
nvidia-smi
```

Если VRAM занята, но процессов нет, вероятно завис CUDA/WSL-контекст.

Ручное восстановление:

```powershell
wsl --shutdown
```

После этого watchdog или ручной запуск снова поднимет WSL и Ollama.

---

## 9. Что в итоге реализовано

Итоговая схема:

- backend проекта обращается к Ollama вместо vLLM;
- Ollama слушает `0.0.0.0:11434`;
- внутри WSL systemd следит за сервисом Ollama;
- systemd timer проверяет `/api/tags` каждые 30 секунд;
- Windows `monitor.ps1` следит за доступностью Ollama снаружи;
- при сбое Windows-скрипт перезапускает WSL и поднимает Ollama;
- для диагностики используются `journalctl`, `curl` и `nvidia-smi`.

---

## 10. Полезные команды

Логи Ollama:

```bash
journalctl -u ollama -f
```

Перезапуск Ollama:

```bash
sudo systemctl restart ollama
```

Остановка WSL:

```powershell
wsl --shutdown
```

Список моделей Ollama:

```bash
ollama list
```

Активные модели:

```bash
ollama ps
```

Проверка API:

```bash
curl http://127.0.0.1:11434/api/tags
```
