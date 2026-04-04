# 02. vLLM On Win11 Host

Если проект на Ubuntu VM лежит не в `~/portfolio`, в следующих файлах замените этот путь на ваш реальный.

Стоп после выполнения этого файла и пришлите мне:

- вывод `wsl --status`;
- вывод `nvidia-smi` внутри WSL;
- вывод `curl.exe http://127.0.0.1:8001/v1/models`.

## Цель шага

Поднять `vLLM` на `Win11 host`, а не внутри Ubuntu VM.

Почему так:

- `ComfyUI` уже живёт на Windows host;
- GPU почти наверняка доступна host, а не VMware VM;
- `vLLM` логичнее запускать рядом с GPU, а не пытаться протащить его в VM без CUDA passthrough.

## 1. Проверяем WSL2

Выполнить на `Win11 host` в PowerShell:

```powershell
wsl --status
wsl --list --verbose
```

Если Ubuntu для WSL ещё нет, выполнить в PowerShell от администратора:

```powershell
wsl --install -d Ubuntu-22.04
```

После установки перезагрузить host и открыть Ubuntu в WSL.

## 2. Готовим WSL-окружение

Выполнить внутри `WSL Ubuntu`:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip git
nvidia-smi
python3 --version
```

Что делаем:

- убеждаемся, что GPU видна внутри WSL;
- подготавливаем Python-окружение под `vLLM`.

Если `nvidia-smi` не работает:

- остановитесь;
- пришлите мне ошибку целиком.

## 3. Ставим vLLM

Выполнить внутри `WSL Ubuntu`:

```bash
python3 -m venv ~/venvs/vllm
source ~/venvs/vllm/bin/activate
pip install --upgrade pip wheel
pip install vllm
```

Что делаем:

- ставим `vLLM` в отдельное окружение, чтобы не смешивать его с Python ComfyUI и системным Python.

## 4. Запускаем первую модель

Выполнить внутри `WSL Ubuntu`:

```bash
source ~/venvs/vllm/bin/activate
export MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_NAME" \
  --host 0.0.0.0 \
  --port 8001 \
  --max-model-len 8192
```

Если модель не помещается в VRAM, остановить процесс и запустить fallback:

```bash
source ~/venvs/vllm/bin/activate
export MODEL_NAME=Qwen/Qwen2.5-3B-Instruct
python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_NAME" \
  --host 0.0.0.0 \
  --port 8001 \
  --max-model-len 8192
```

Что делаем:

- поднимаем первый OpenAI-compatible endpoint;
- пока не делаем службу, запускаем вручную для smoke test.

Оставьте это окно открытым.

## 5. Проверяем vLLM локально на host

В новом окне PowerShell на `Win11 host` выполнить:

```powershell
curl.exe http://127.0.0.1:8001/v1/models
```

Что делаем:

- убеждаемся, что `vLLM` отвечает локально на Windows host.

## 6. Пробрасываем порт vLLM наружу для VMware VM

Выполнить на `Win11 host` в PowerShell от администратора:

```powershell
netsh interface portproxy show all
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=8001
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8001 connectaddress=127.0.0.1 connectport=8001
New-NetFirewallRule -DisplayName "vLLM-8001" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8001
```

Если `delete` ругнётся, это нормально. Идём дальше.

Что делаем:

- даём VMware VM доступ к `vLLM`, который слушает внутри WSL.

## Критерий успеха

Успешным считаем шаг, если:

- `nvidia-smi` работает внутри WSL;
- `vLLM` поднялся;
- `curl.exe http://127.0.0.1:8001/v1/models` возвращает JSON.
