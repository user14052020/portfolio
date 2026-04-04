# 03. VM Env And Smoke Tests

Если проект на Ubuntu VM лежит не в `~/portfolio`, замените этот путь в командах ниже на ваш реальный путь к репозиторию.

Стоп после выполнения этого файла и пришлите мне:

- вывод `curl` до `vLLM` из VM;
- вывод `curl` до `vLLM` из backend контейнера;
- итоговые строки `COMFYUI_BASE_URL` и `VLLM_BASE_URL` из `.env`.

## Цель шага

Подготовить Ubuntu VM и контейнер backend к работе с:

- `ComfyUI` на Windows host;
- `vLLM` на Windows host.

## 1. Переходим в проект

Выполнить в `Ubuntu VM`:

```bash
cd ~/portfolio
pwd
ls
```

## 2. Сохраняем резервную копию `.env`

Выполнить в `Ubuntu VM`:

```bash
cd ~/portfolio
cp .env .env.before-host-ai
```

Что делаем:

- делаем backup перед изменением адресов внешних AI-сервисов.

## 3. Проверяем vLLM из самой VM

Выполнить в `Ubuntu VM`:

```bash
curl -fsS http://<WIN_HOST_IP>:8001/v1/models
```

Что делаем:

- проверяем, что `Ubuntu VM` видит `vLLM` на Windows host.

Если тут ошибка:

- остановитесь;
- пришлите мне вывод;
- шаги ниже пока не делайте.

## 4. Проверяем vLLM из backend контейнера

Выполнить в `Ubuntu VM`:

```bash
cd ~/portfolio
docker compose exec backend curl -fsS http://<WIN_HOST_IP>:8001/v1/models
docker compose exec backend curl -fsS http://<WIN_HOST_IP>:8188/ > /dev/null && echo "COMFYUI_OK"
```

Что делаем:

- убеждаемся, что не только VM, но и backend контейнер видит оба AI-сервиса на host.

## 5. Обновляем `.env`

Выполнить в `Ubuntu VM`:

```bash
cd ~/portfolio
export WIN_HOST_IP=<WIN_HOST_IP>
sed -i.bak "s|^COMFYUI_BASE_URL=.*|COMFYUI_BASE_URL=http://${WIN_HOST_IP}:8188|" .env
grep -q '^VLLM_BASE_URL=' .env && sed -i "s|^VLLM_BASE_URL=.*|VLLM_BASE_URL=http://${WIN_HOST_IP}:8001/v1|" .env || printf '\nVLLM_BASE_URL=http://%s:8001/v1\n' "$WIN_HOST_IP" >> .env
grep -n 'COMFYUI_BASE_URL\|VLLM_BASE_URL' .env
```

Что делаем:

- фиксируем реальные адреса Windows host в конфиге проекта;
- пока код ещё не использует `VLLM_BASE_URL`, но значение уже готово для следующего шага.

## 6. Проверяем переменные ещё раз

Выполнить в `Ubuntu VM`:

```bash
cd ~/portfolio
grep -n 'COMFYUI_BASE_URL\|VLLM_BASE_URL' .env
```

## Критерий успеха

Успешным считаем шаг, если:

- `Ubuntu VM` достучалась до `http://<WIN_HOST_IP>:8001/v1/models`;
- backend контейнер достучался до `vLLM` и `ComfyUI`;
- `.env` содержит корректные `COMFYUI_BASE_URL` и `VLLM_BASE_URL`.
