# 04. Application vLLM Integration

Если проект на Ubuntu VM лежит не в `~/portfolio`, замените этот путь в командах ниже на ваш реальный путь к репозиторию.

Этот файл выполняем только после того, как:

- шаг `01` зелёный;
- шаг `02` зелёный;
- шаг `03` зелёный;
- я внесу кодовые правки под `vLLM`.

Стоп после выполнения этого файла и пришлите мне:

- вывод smoke test на endpoint стилиста;
- логи backend после запроса;
- описание того, что вернулось в UI.

## Цель шага

Подключить backend проекта к `vLLM`, не ломая текущую генерацию через `ComfyUI`.

## Что именно будем менять в коде

На этом этапе я буду менять в репозитории:

- backend config;
- клиент к `vLLM`;
- prompt policy;
- routing логики:
  - только текст;
  - текст + генерация;
  - текст + каталог;
- fallback, если `vLLM` не отвечает.

## Команды, которые вы выполните после моих кодовых правок

Выполнить в `Ubuntu VM`:

```bash
cd ~/portfolio
grep -n 'VLLM_BASE_URL\|COMFYUI_BASE_URL' .env
docker compose up --build -d backend frontend
docker compose logs --tail=200 backend
```

Что делаем:

- пересобираем `backend` и `frontend`;
- убеждаемся, что backend стартует с новыми env.

## Smoke test backend API

Выполнить в `Ubuntu VM`:

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

Что делаем:

- проверяем, что текстовый reasoning уже идёт не из mock-логики, а из `vLLM`.

## Smoke test с генерацией

Выполнить в `Ubuntu VM`:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/stylist-chat/message \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "manual-vllm-test-2",
    "locale": "ru",
    "message": "У меня белая рубашка, подбери что с ней надеть и сгенерируй пример образа.",
    "auto_generate": true
  }'
```

Что делаем:

- проверяем, что backend одновременно:
  - получает reasoning из `vLLM`;
  - при необходимости ставит image generation job в `ComfyUI`.

## Логи после теста

Выполнить в `Ubuntu VM`:

```bash
cd ~/portfolio
docker compose logs --tail=200 backend
```

## Критерий успеха

Успешным считаем шаг, если:

- backend отвечает на текстовый запрос;
- тон ответа уже управляется prompt policy;
- запрос с `auto_generate=true` создаёт generation job;
- UI не блокируется надолго на отправке.
