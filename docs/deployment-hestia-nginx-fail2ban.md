# Деплой portfolio на HestiaCP, Nginx и Fail2Ban

Документ фиксирует рабочую схему для `maharram.ru`: Docker-приложение живет на Ubuntu VM, HestiaCP/Nginx принимает `80/443`, проксирует Next.js и FastAPI, пишет access/error логи и банит агрессивный трафик через Fail2Ban.

Секреты, пароли и приватные ключи в этот файл не добавляются.

## Текущая схема

- Внешний домен: `maharram.ru`, `www.maharram.ru`.
- Внешний IP: `31.25.31.72`.
- Ubuntu VM IP: `192.168.100.10`.
- Docker-проект на Ubuntu: `/home/web/projects/portfolio`.
- Hestia web user/domain: `portfolio` / `maharram.ru`.
- Frontend: `127.0.0.1:3000` внутри Ubuntu host namespace, контейнер `portfolio-frontend`.
- Backend API/media: `127.0.0.1:8000`, контейнер `portfolio-backend`.
- Hestia proxy template: `portfolio-next`.
- SSL: Let's Encrypt включен для `maharram.ru` и `www.maharram.ru`.

Если сайт находится за Windows host/Hyper-V, на Windows должны быть пробросы:

```powershell
netsh interface portproxy show all
```

Ожидаемо:

```text
0.0.0.0:80  -> 192.168.100.10:80
0.0.0.0:443 -> 192.168.100.10:443
```

Не надо пробрасывать внешний `80/443` напрямую на `3000`: тогда Hestia/Nginx/Fail2Ban/SSL/логи будут обходиться.

## DNS

У регистратора:

```text
maharram.ru.      A      31.25.31.72
www.maharram.ru.  A      31.25.31.72
```

Проверка:

```bash
dig +short A maharram.ru
dig +short A www.maharram.ru
dig +short AAAA maharram.ru
```

`AAAA` лучше не задавать, если IPv6 реально не настроен.

## Docker production

Основные файлы проекта:

- `docker-compose.yml`
- `.env`
- `apps/frontend/Dockerfile`
- `apps/backend/Dockerfile`
- `apps/frontend/package.json`
- `apps/frontend/package-lock.json`
- `apps/backend/requirements.txt`

Frontend должен запускаться в production:

```yaml
frontend:
  environment:
    NODE_ENV: production
    NEXT_TELEMETRY_DISABLED: "1"
    NEXT_PUBLIC_API_URL: /api/v1
    INTERNAL_API_URL: http://backend:8000/api/v1
    NEXT_PUBLIC_MEDIA_URL: /media
    NEXT_PUBLIC_SITE_URL: https://maharram.ru
  command: npm run start -- --hostname 0.0.0.0
```

Backend:

```yaml
backend:
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Команды после rsync/заливки:

```bash
cd /home/web/projects/portfolio
sudo docker compose up -d --build --force-recreate
sudo docker compose exec backend alembic upgrade head
sudo docker compose exec backend python scripts/seed_showcase_projects.py --replace
```

Если есть Alembic `Multiple head revisions`, сначала проверить:

```bash
sudo docker compose exec backend alembic heads --verbose
```

Проверить, что frontend не dev:

```bash
sudo docker compose exec frontend sh -lc 'ps -ef; echo NODE_ENV=$NODE_ENV'
```

Должно быть `next start`, не `next dev`; в логах не должно быть `/_next/webpack-hmr`.

При rsync желательно использовать `--delete`, иначе старые `.ts` файлы на Ubuntu могут оставаться и ломать production build:

```bash
rsync -av --delete ./portfolio/ web@192.168.100.10:/home/web/projects/portfolio/
```

## HestiaCP: домен и шаблон

Проверка домена:

```bash
sudo /usr/local/hestia/bin/v-list-web-domain portfolio maharram.ru json
```

Важные значения:

```text
IP='192.168.100.10'
PROXY='portfolio-next'
SSL='yes'
LETSENCRYPT='yes'
```

Назначение proxy template:

```bash
sudo /usr/local/hestia/bin/v-change-web-domain-proxy-tpl portfolio maharram.ru portfolio-next "<PROXY_EXT>" no
sudo /usr/local/hestia/bin/v-rebuild-web-domain portfolio maharram.ru yes
sudo nginx -t
```

Где `<PROXY_EXT>` можно взять из:

```bash
sudo grep "DOMAIN='maharram.ru'" /usr/local/hestia/data/users/portfolio/web.conf
```

## Hestia/Nginx файлы

Шаблоны, которые нужно перенести на новый сервер:

```text
/usr/local/hestia/data/templates/web/nginx/portfolio-next.tpl
/usr/local/hestia/data/templates/web/nginx/portfolio-next.stpl
```

Сгенерированные Hestia файлы домена, руками их не считать источником правды:

```text
/home/portfolio/conf/web/maharram.ru/nginx.conf
/home/portfolio/conf/web/maharram.ru/nginx.ssl.conf
/etc/nginx/conf.d/domains/maharram.ru.conf
/etc/nginx/conf.d/domains/maharram.ru.ssl.conf
```

`nginx.conf_custom` должен быть пустым или содержать только доп. правила без `location /`, потому что Hestia включает `nginx.conf_*` внутрь `server {}`:

```text
/home/portfolio/conf/web/maharram.ru/nginx.conf_custom
```

Проверка конфликтов:

```bash
sudo nginx -t
sudo nginx -T 2>/dev/null | grep -nE 'maharram.ru|proxy_pass|limit_req|access_log'
```

## Rate limit Nginx

Файл:

```text
/etc/nginx/conf.d/maharram-rate-limit.conf
```

Содержимое:

```nginx
limit_req_zone $binary_remote_addr zone=maharram_site:20m rate=30r/s;
limit_req_zone $binary_remote_addr zone=maharram_api:20m rate=10r/s;
limit_req_status 429;
limit_req_log_level warn;
```

В template `portfolio-next` используются:

```nginx
limit_req zone=maharram_site burst=10 nodelay;
limit_req zone=maharram_api burst=10 nodelay;
```

Расшифровка:

- `maharram_site`: nginx пропускает до `30` запросов в секунду от одного IP по основным страницам. Короткий всплеск до `10` запросов допускается через `burst`, после превышения nginx отвечает `429` и пишет `limiting requests` в error log.
- `maharram_api`: nginx пропускает до `10` запросов в секунду от одного IP по `/api/`. Короткий всплеск до `10` запросов допускается через `burst`.
- Эти числа не банят IP сами по себе. Они только ограничивают поток запросов и создают записи в `/var/log/apache2/domains/maharram.ru.error.log`, которые потом читает Fail2Ban.

Типовые сканерские пути отсекаются на Nginx уровне через `return 444`, например:

```text
/wp-login.php
/xmlrpc.php
/.env
/phpmyadmin
/wp-admin
```

## SSL Let's Encrypt

Выпуск:

```bash
sudo /usr/local/hestia/bin/v-add-letsencrypt-domain portfolio maharram.ru www.maharram.ru no
sudo /usr/local/hestia/bin/v-rebuild-web-domain portfolio maharram.ru yes
```

Проверка:

```bash
openssl x509 -in /home/portfolio/conf/web/maharram.ru/ssl/maharram.ru.pem -noout -subject -issuer -dates
curl -I https://maharram.ru/
```

Лог выпуска:

```text
/var/log/hestia/LE-portfolio-maharram.ru.log
```

Важно: template должен подключать временный файл Hestia для ACME:

```nginx
include %home%/%user%/conf/web/%domain%/nginx.conf_letsencrypt*;
include %home%/%user%/conf/web/%domain%/nginx.ssl.conf_letsencrypt*;
```

## Логи сайта

Даже если запросы принимает Nginx, Hestia в этой установке пишет доменные логи в каталог `apache2`:

```text
/var/log/apache2/domains/maharram.ru.log
/var/log/apache2/domains/maharram.ru.error.log
/var/log/apache2/domains/maharram.ru.bytes
```

Смотреть онлайн:

```bash
sudo tail -f /var/log/apache2/domains/maharram.ru.log /var/log/apache2/domains/maharram.ru.error.log
```

Полезные проверки:

```bash
curl -I -H 'Host: maharram.ru' http://192.168.100.10/
curl -k -I -H 'Host: maharram.ru' https://192.168.100.10/
curl -I https://maharram.ru/
```

## Fail2Ban

Файлы:

```text
/etc/fail2ban/jail.d/maharram-nginx.conf
/etc/fail2ban/filter.d/maharram-nginx-badpaths.conf
/usr/local/sbin/fail2ban-ignore-verified-search-bot
/etc/fail2ban/filter.d/nginx-limit-req.conf
/etc/fail2ban/action.d/hestia.conf
```

Активные jail:

```text
maharram-nginx-limit-req
maharram-nginx-badpaths
```

`maharram-nginx-limit-req` читает:

```text
/var/log/apache2/domains/maharram.ru.error.log
```

Текущие пороги jail:

```ini
maxretry = 10
findtime = 60
bantime = 3600
```

То есть IP будет забанен на `3600` секунд, если за `60` секунд он `10` раз попал в nginx `limit_req` и получил ограничение по частоте запросов. На практике это значит: один резкий всплеск nginx просто притормозит/отдаст `429`, а повторяющийся агрессивный поток от одного IP уже попадет в бан.

`maharram-nginx-badpaths` читает:

```text
/var/log/apache2/domains/maharram.ru.log
```

И банит сканеры, которые ходят по `.env`, `wp-admin`, `wp-login.php`, `phpmyadmin`, `xmlrpc.php` и т.д. Путь `/admin` не добавляется в badpaths, потому что там живет админка приложения.

Проверка конфига:

```bash
sudo fail2ban-client -t
sudo fail2ban-client status
sudo fail2ban-client status maharram-nginx-limit-req
sudo fail2ban-client status maharram-nginx-badpaths
```

Перезагрузка:

```bash
sudo fail2ban-client reload
sudo systemctl restart fail2ban
```

Разбанить IP:

```bash
sudo fail2ban-client set maharram-nginx-limit-req unbanip 1.2.3.4
sudo fail2ban-client set maharram-nginx-badpaths unbanip 1.2.3.4
```

Логи Fail2Ban:

```text
/var/log/fail2ban.log
```

Hestia action банит через:

```text
/usr/local/hestia/bin/v-add-firewall-ban
/usr/local/hestia/bin/v-delete-firewall-ban
```

Проверить firewall Hestia:

```bash
sudo /usr/local/hestia/bin/v-list-firewall
sudo /usr/local/hestia/bin/v-list-firewall-ban
```

## Google/Yandex bots

Файл:

```text
/usr/local/sbin/fail2ban-ignore-verified-search-bot
```

Он не доверяет User-Agent, а проверяет reverse DNS и forward DNS для доменов:

```text
*.googlebot.com
*.google.com
*.yandex.ru
*.yandex.net
*.yandex.com
```

Проверка вручную:

```bash
sudo /usr/local/sbin/fail2ban-ignore-verified-search-bot 66.249.66.1
echo $?
```

Код `0` значит verified search bot, Fail2Ban должен игнорировать IP.

## Важное про реальный IP посетителя

Если Ubuntu стоит за Windows `netsh portproxy` или NAT, в логах может быть не реальный IP посетителя, а IP прокси/шлюза, например:

```text
192.168.100.1
31.25.31.72
```

В таком случае Nginx rate limit все равно защищает Next.js от перегруза, но точечный бан реального внешнего IP на Ubuntu невозможен, потому что до Ubuntu этот IP уже не доходит.

Для полноценного бана реальных IP нужно:

- пробрасывать трафик не через `netsh portproxy`, а на уровне роутера/NAT с сохранением source IP;
- либо ставить reverse proxy/Firewall на Windows host;
- либо выносить Nginx на узел, который первым принимает внешний трафик.

## Чистый Nginx без Hestia

Минимальная схема:

```nginx
limit_req_zone $binary_remote_addr zone=maharram_site:20m rate=30r/s;
limit_req_zone $binary_remote_addr zone=maharram_api:20m rate=10r/s;

server {
    listen 80;
    server_name maharram.ru www.maharram.ru;

    access_log /var/log/nginx/maharram.ru.access.log combined;
    error_log  /var/log/nginx/maharram.ru.error.log warn;

    location ^~ /.well-known/acme-challenge/ {
        root /var/www/maharram.ru;
        try_files $uri =404;
    }

    location ~* ^/(?:wp-login\.php|xmlrpc\.php|wp-admin|wp-content|phpmyadmin|\.env|vendor/phpunit|boaform|cgi-bin|shell|adminer) {
        return 444;
    }

    location ^~ /api/ {
        limit_req zone=maharram_api burst=10 nodelay;
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ^~ /media/ {
        limit_req zone=maharram_site burst=10 nodelay;
        proxy_pass http://127.0.0.1:8000/media/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        limit_req zone=maharram_site burst=10 nodelay;
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

SSL:

```bash
sudo certbot --nginx -d maharram.ru -d www.maharram.ru
```

## Чистый Apache без Hestia

Если Nginx не используется, Apache может быть reverse proxy:

```apache
<VirtualHost *:80>
    ServerName maharram.ru
    ServerAlias www.maharram.ru

    CustomLog ${APACHE_LOG_DIR}/maharram.ru.access.log combined
    ErrorLog  ${APACHE_LOG_DIR}/maharram.ru.error.log

    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "http"

    ProxyPass        /api/   http://127.0.0.1:8000/api/
    ProxyPassReverse /api/   http://127.0.0.1:8000/api/

    ProxyPass        /media/ http://127.0.0.1:8000/media/
    ProxyPassReverse /media/ http://127.0.0.1:8000/media/

    ProxyPass        /       http://127.0.0.1:3000/
    ProxyPassReverse /       http://127.0.0.1:3000/
</VirtualHost>
```

Модули:

```bash
sudo a2enmod proxy proxy_http headers ssl rewrite
sudo systemctl reload apache2
```

Для защиты на Apache лучше дополнительно ставить Nginx перед Apache или использовать `mod_evasive` плюс Fail2Ban по Apache логам.

## Быстрый чек-лист после деплоя

```bash
cd /home/web/projects/portfolio
sudo docker compose ps
sudo docker compose exec frontend sh -lc 'ps -ef; echo NODE_ENV=$NODE_ENV'
sudo docker compose exec backend alembic current

sudo nginx -t
sudo systemctl status nginx --no-pager
sudo fail2ban-client status

curl -I http://maharram.ru/
curl -I https://maharram.ru/
sudo tail -n 30 /var/log/apache2/domains/maharram.ru.log
sudo tail -n 30 /var/log/apache2/domains/maharram.ru.error.log
```

Внешняя проверка доступности:

```text
https://check-host.net/check-http?host=https://maharram.ru/
```
