# Что Такое API И HTTP

Это следующий фундаментальный шаг курса.

После этой главы слова `API`, `HTTP`, `request`, `response`, `method`, `headers`, `status code`, `JSON`, `query`, `body`, `endpoint`, `client` и `server` уже не должны быть просто шумом.

Именно здесь становится по-настоящему понятно:
- как frontend разговаривает с backend;
- почему браузер вообще может “отправить сообщение стилисту”;
- почему backend понимает, что от него хотят;
- как один процесс обращается к другому по сети.

## Что Это Академически

### API

API, или Application Programming Interface, — это формализованный интерфейс взаимодействия программных компонентов, определяющий, какие операции доступны, в каком формате передаются данные и какие ответы могут быть возвращены.

Проще и точнее:
- API — это договор;
- одна сторона обещает принимать определённые запросы;
- другая сторона обязуется отправлять их в правильной форме.

### HTTP

HTTP, или Hypertext Transfer Protocol, — это прикладной сетевой протокол, предназначенный для передачи запросов и ответов между клиентом и сервером.

Он задаёт:
- формат запроса;
- формат ответа;
- методы;
- заголовки;
- статус-коды;
- правила передачи тела сообщения.

### Клиент

Клиент — это сторона, которая инициирует запрос.

В веб-приложении клиентом может быть:
- браузер;
- frontend-приложение;
- мобильное приложение;
- другой backend-сервис;
- даже терминальная команда `curl`.

### Сервер

Сервер — это сторона, которая принимает запрос, обрабатывает его и возвращает ответ.

### Request

HTTP request — это структурированное сообщение от клиента к серверу.

Обычно в нём есть:
- method;
- URL;
- headers;
- query parameters;
- body.

### Response

HTTP response — это структурированное сообщение от сервера обратно клиенту.

Обычно в нём есть:
- статус-код;
- headers;
- body.

### Method

HTTP method — это тип действия, которое клиент хочет выполнить.

Чаще всего:
- `GET` — получить данные;
- `POST` — создать действие или отправить данные на обработку;
- `PUT` — заменить ресурс;
- `PATCH` — частично изменить ресурс;
- `DELETE` — удалить ресурс.

### Headers

HTTP headers — это служебные метаданные запроса или ответа.

Через них передают, например:
- тип содержимого;
- авторизацию;
- кэш-политику;
- информацию о допустимом формате.

### Status Code

HTTP status code — это стандартизированный числовой код результата обработки запроса.

Например:
- `200 OK` — запрос успешно обработан;
- `201 Created` — ресурс создан;
- `204 No Content` — всё хорошо, но тела ответа нет;
- `400 Bad Request` — клиент прислал некорректный запрос;
- `401 Unauthorized` — нужна авторизация;
- `404 Not Found` — ресурс не найден;
- `500 Internal Server Error` — ошибка на стороне сервера.

### URL И Endpoint

URL — это адрес, по которому клиент обращается к серверу.

Endpoint — это конкретная точка API, то есть конкретный путь и действие, которое сервер умеет обрабатывать.

Например:
- `/health`
- `/api/v1/stylist-chat/message`
- `/api/v1/stylist-chat/history/{session_id}`

### Query Parameters

Query parameters — это параметры, передаваемые в URL после `?`.

Пример:

```text
/projects?q=minimal&featured_only=true
```

### Body

Body — это основное тело HTTP-запроса или ответа.

В body часто передают:
- JSON;
- form-data;
- текст;
- бинарные данные;
- файлы.

### JSON

JSON, или JavaScript Object Notation, — это текстовый формат обмена структурированными данными.

Он очень популярен в API, потому что:
- его легко генерировать;
- его легко читать;
- его понимают и frontend, и backend, и многие другие системы.

## Что Это Простыми Словами

Если по-человечески:

- API — это меню и правила заказа;
- HTTP — это способ, которым заказ доезжает до кухни;
- клиент — это тот, кто делает заказ;
- сервер — это кухня;
- request — это сам заказ;
- response — это то, что кухня вернула обратно;
- status code — это короткий итог: получилось или нет;
- headers — это служебные пометки на заказе;
- body — это основное содержимое заказа.

То есть когда пользователь пишет в чат на сайте, на самом деле происходит не “магия чата”, а вполне строгий обмен:
- frontend формирует request;
- backend принимает request;
- backend отдаёт response;
- frontend читает response и показывает его пользователю.

## Почему Это Реализовано Именно Так

Проект разделён на frontend и backend, и им нужен формальный способ общаться между собой.

Почему не сделать “просто прямой вызов функции”:
- frontend и backend живут в разных процессах;
- они могут жить на разных портах;
- иногда даже на разных машинах;
- им нужен общий сетевой договор.

HTTP и API решают эту задачу:
- frontend знает, по какому URL идти;
- backend знает, какой метод и какой payload принять;
- обе стороны понимают JSON;
- обе стороны могут отдельно развиваться, пока договор API сохраняется.

## Какие Anti-Patterns Рядом Существуют

### Anti-pattern 1. Думать, что API = только интернет

Нет.

API бывает не только “удалённым интернет-API”.

API — это вообще интерфейс взаимодействия программ.

Но в этой главе мы говорим именно про HTTP API, то есть сетевой API поверх HTTP.

### Anti-pattern 2. Думать, что request — это просто “отправили строку”

HTTP-запрос — это структурированное сообщение.

У него есть:
- method;
- URL;
- headers;
- иногда body;
- иногда query parameters.

### Anti-pattern 3. Игнорировать status code

Очень частая ошибка новичка — смотреть только в body и не учитывать код ответа.

На практике:
- `200` и `500` — это принципиально разные ситуации;
- даже одинаковый текст в body не делает их одинаковыми.

### Anti-pattern 4. Путать query и body

`query` — это параметры в URL.

`body` — это основное содержимое запроса.

Например:
- фильтры списка часто передают через query;
- создание сущности часто передают через JSON body.

### Anti-pattern 5. Думать, что GET и POST различаются “только названием”

На практике это разные типы намерения.

Даже если сервер может быть написан так, что “и так, и так работает”, инженерно это плохой стиль.

## Что Реализовано В Этом Проекте

### 1. Backend публикует HTTP API под `/api/v1`

Это видно в:

- `apps/backend/app/main.py:56`

Там backend подключает роутер с префиксом:

```python
app.include_router(api_router, prefix=settings.api_v1_prefix)
```

А значит все прикладные маршруты backend живут под версией API:

```text
/api/v1/...
```

Это хороший engineering-подход:
- API можно версионировать;
- старые и новые контракты проще разделять;
- проект лучше готов к развитию.

### 2. У backend есть отдельный health endpoint

Это видно в:

- `apps/backend/app/main.py:60`
- `apps/backend/app/main.py:61`

Там есть:

```python
@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
```

Это минимальный HTTP endpoint для проверки того, что backend-процесс вообще жив.

### 3. Общий роутер собирает API из отдельных модулей

Это видно в:

- `apps/backend/app/api/router.py`

Там подключаются маршруты:
- `auth`
- `users`
- `projects`
- `blog_posts`
- `contact_requests`
- `site_settings`
- `uploads`
- `stylist_chat`
- `generation_jobs`

Это значит, что API проекта не лежит в одном гигантском файле, а собирается из модулей.

### 4. У нас есть реальный POST endpoint для отправки сообщения стилисту

Это видно в:

- `apps/backend/app/api/routes/stylist_chat.py:11`
- `apps/backend/app/api/routes/stylist_chat.py:14`
- `apps/backend/app/api/routes/stylist_chat.py:19`
- `apps/backend/app/api/routes/stylist_chat.py:20`

Там объявлен endpoint:

```text
POST /stylist-chat/message
```

После общего префикса API полный путь становится таким:

```text
/api/v1/stylist-chat/message
```

А семантика такая:
- клиент отправляет body с сообщением;
- backend валидирует payload;
- сервис обрабатывает сообщение;
- backend коммитит изменения в сессию и возвращает структурированный ответ.

### 5. У нас есть реальный GET endpoint для чтения истории чата

Это видно в:

- `apps/backend/app/api/routes/stylist_chat.py:24`
- `apps/backend/app/api/routes/stylist_chat.py:29`

Там объявлен endpoint:

```text
GET /stylist-chat/history/{session_id}
```

Это уже другой тип API-вызова:
- он получает данные;
- использует path parameter;
- не создаёт новое сообщение;
- возвращает историю.

Это хороший практический пример разницы между `GET` и `POST`.

### 6. Frontend строит URL и отправляет HTTP-запросы через fetch

Это видно в:

- `apps/frontend/src/shared/api/client.ts:23`
- `apps/frontend/src/shared/api/client.ts:47`

Там:
- `buildUrl(...)` собирает итоговый URL;
- `fetch(...)` выполняет HTTP-запрос.

То есть frontend сам является HTTP-клиентом.

### 7. Frontend выставляет headers

Это видно в:

- `apps/frontend/src/shared/api/client.ts:40`
- `apps/frontend/src/shared/api/client.ts:41`
- `apps/frontend/src/shared/api/client.ts:44`

Там видно два важных примера headers:

- `Content-Type: application/json`
- `Authorization: Bearer ...`

Это очень важная часть HTTP:
- body без правильного `Content-Type` может быть непонятен серверу;
- защищённые endpoints требуют auth headers.

### 8. Frontend обрабатывает status code и response body

Это видно в:

- `apps/frontend/src/shared/api/client.ts:54`
- `apps/frontend/src/shared/api/client.ts:55`
- `apps/frontend/src/shared/api/client.ts:85`

Логика такая:
- если `response.ok` ложный, читается текст ошибки;
- если можно, ошибка разбирается как JSON;
- если всё хорошо, response превращается в JSON.

То есть frontend в проекте не просто “шлёт запрос”, а ещё и интерпретирует HTTP-ответ.

### 9. В проекте используются и JSON body, и FormData

JSON body видно, например, в:

- `apps/frontend/src/shared/api/client.ts:275`
- `apps/frontend/src/shared/api/client.ts:296`

Например:
- сообщение стилисту отправляется как JSON;
- создание generation job тоже идёт через JSON.

`FormData` видно в:

- `apps/frontend/src/shared/api/client.ts:38`
- `apps/frontend/src/shared/api/client.ts:259`

Это используется для загрузки файлов.

Значит, проект уже показывает два разных практических типа HTTP-body:
- JSON;
- multipart form-data.

### 10. Frontend и backend действительно общаются по сети, а не “внутри одного файла”

Это видно по:

- `docker-compose.yml:85`
- `docker-compose.yml:91`
- `docker-compose.yml:103`
- `docker-compose.yml:109`

Где:
- backend публикуется на `8000`;
- frontend публикуется на `3000`;
- frontend внутри окружения знает internal URL backend.

То есть в проекте HTTP — это не абстракция из учебника, а реальный рабочий протокол связи между процессами.

## JSON, Query, Path Parameters И Body На Простом Примере

Возьмём воображаемый endpoint:

```text
GET /books/42?locale=ru
```

Тут:
- `/books/42` — путь;
- `42` — path parameter;
- `locale=ru` — query parameter;
- method — `GET`;
- body обычно отсутствует.

А теперь другой пример:

```text
POST /books
Content-Type: application/json
```

С body:

```json
{
  "title": "Tailoring Basics",
  "author": "Mira Vale"
}
```

Тут:
- метод уже `POST`;
- данные лежат в JSON body;
- это уже не “получить”, а “передать новую сущность на обработку”.

## Разбор На Примере

### Простой Вымышленный Пример

Представим маленький сервис `notes-api`.

У него могут быть такие endpoints:

- `GET /notes` — получить список заметок;
- `GET /notes/15` — получить одну заметку;
- `POST /notes` — создать заметку;
- `DELETE /notes/15` — удалить заметку.

Если клиент отправляет:

```http
POST /notes
Content-Type: application/json
```

И body:

```json
{
  "title": "Buy fabric",
  "done": false
}
```

то сервер может ответить:

```http
201 Created
Content-Type: application/json
```

и вернуть созданную заметку.

### Пример Из Текущего Проекта

Когда пользователь отправляет сообщение стилисту, происходит примерно такая цепочка:

1. Frontend вызывает `sendStylistMessage(...)` в `apps/frontend/src/shared/api/client.ts:275`.
2. Эта функция отправляет `POST` запрос на `/stylist-chat/message`.
3. Backend endpoint в `apps/backend/app/api/routes/stylist_chat.py:14` принимает payload.
4. Сервис обрабатывает сообщение.
5. Backend возвращает JSON-ответ.
6. Frontend читает JSON и отображает результат в UI.

А когда frontend хочет историю чата:

1. Он вызывает `getChatHistory(...)` в `apps/frontend/src/shared/api/client.ts:292`.
2. Уходит `GET` запрос на `/stylist-chat/history/{session_id}`.
3. Backend endpoint в `apps/backend/app/api/routes/stylist_chat.py:24` возвращает список сообщений.

Это уже не учебная схема, а реальная жизнь проекта.

## Где Это Видно В Коде И Конфигах

### Frontend

- `apps/frontend/src/shared/api/client.ts`
- `apps/frontend/src/shared/config/env.ts`
- `apps/frontend/src/features/chat/model/useStylistChatSimple.ts`

### Backend

- `apps/backend/app/main.py`
- `apps/backend/app/api/router.py`
- `apps/backend/app/api/routes/stylist_chat.py`
- `apps/backend/app/schemas/stylist.py`

### Инфраструктура

- `docker-compose.yml`
- `.env.example`

## Что Ещё Можно Улучшить

На уровне инженерного мышления здесь дальше полезно будет отдельно разобрать:
- чем REST API отличается от просто “набора HTTP-endpoints”;
- как проектировать ошибки API;
- чем path parameters отличаются от query на уровне design;
- как документировать API;
- как версионирование API помогает не ломать клиентов;
- где в будущем уместен polling, а где лучше WebSockets.

Эти темы уже логично ведут нас к следующим главам, а не теряются отдельно от проекта.

## Команды

### Проверить health backend

```bash
curl http://127.0.0.1:8000/health
```

### Отправить сообщение стилисту вручную

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/stylist-chat/message \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"manual-demo\",\"locale\":\"ru\",\"message\":\"Помоги собрать образ\",\"auto_generate\":false}"
```

### Получить историю чата вручную

```bash
curl -sS http://127.0.0.1:8000/api/v1/stylist-chat/history/manual-demo
```

### Посмотреть, какие методы и пути мы уже используем на фронте

```bash
rg -n "method:|fetch\\(|FormData|Authorization|Content-Type" apps/frontend/src/shared/api/client.ts
```

## Мини-Упражнения

1. Объясните своими словами разницу между `API` и `HTTP`.
2. Объясните, почему `POST /stylist-chat/message` и `GET /stylist-chat/history/{session_id}` — это разные типы HTTP-взаимодействия.
3. Назовите пример header из текущего проекта и объясните, зачем он нужен.
4. Объясните разницу между `query`, `path parameter` и `body`.
5. Своими словами ответьте, почему frontend не может просто “вызвать Python-функцию backend напрямую”.

## Что Читать Дальше

После этой главы логично идти так:

1. что такое база данных;
2. чем SQL отличается от NoSQL;
3. что такое кэш и поиск;
4. чем REST отличается от GraphQL.
