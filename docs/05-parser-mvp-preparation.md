# 05. Parser MVP Preparation

Если проект на Ubuntu VM лежит не в `~/portfolio`, замените этот путь в командах ниже на ваш реальный путь к репозиторию.

Этот файл пока не исполняем до конца. Сначала доводим `vLLM + ComfyUI` до рабочего состояния.

Когда дойдём до parser phase, вы выполните команды ниже и пришлёте мне:

- список 1-2 источников;
- robots.txt;
- пример карточки товара;
- пример HTML listing page.

## Цель шага

Подготовить parser как отдельный контур, а не как часть chat request.

## 1. Готовим рабочие директории

Выполнить в `Ubuntu VM`:

```bash
cd ~/portfolio
mkdir -p data/parser/raw
mkdir -p data/parser/normalized
mkdir -p data/parser/images
mkdir -p data/parser/logs
mkdir -p notes/sources
printf 'source_name,base_url,robots_url,city,notes\n' > notes/sources/local-secondhand-sources.csv
find data/parser -maxdepth 2 -type d | sort
ls -l notes/sources
```

Что делаем:

- создаём каркас под parser pipeline;
- заводим место, где будем хранить список кандидатов-источников.

## 2. Проверяем первый источник вручную

Выполнить в `Ubuntu VM`:

```bash
export SOURCE_URL='https://REPLACE_ME'
curl -I "$SOURCE_URL"
curl -fsS "${SOURCE_URL%/}/robots.txt" | sed -n '1,120p'
```

Что делаем:

- смотрим, что за сайт;
- проверяем robots.txt;
- не начинаем scraping вслепую.

## 3. Сохраняем первый источник в CSV

Выполнить в `Ubuntu VM`:

```bash
cd ~/portfolio
printf 'site_1,%s,%s,REPLACE_CITY,manual check pending\n' "$SOURCE_URL" "${SOURCE_URL%/}/robots.txt" >> notes/sources/local-secondhand-sources.csv
cat notes/sources/local-secondhand-sources.csv
```

## Что будет следующим после этого шага

После того как `vLLM + ComfyUI` стабильно работают, я подготовлю:

- backend schema для offers;
- parser script skeleton;
- нормализацию карточек;
- matching слой между recommendation JSON и каталогом.

## Критерий успеха

Успешным считаем шаг, если:

- у нас есть хотя бы 1 подтверждённый источник;
- robots.txt проверен;
- структура папок под parser уже создана;
- дальше можно без хаоса переходить к first adapter implementation.
