Готово, поднял на Win11 host связку **Nginx + IPBan**.

Что сейчас работает:

- `netsh portproxy` для `80/443` удален.
- `80/443` на Win11 теперь слушает `nginx/1.30.2`.
- `maharram.ru`, `dental.maharram.ru`, `1c.maharram.ru` открываются через Win11 Nginx.
- Win11 Nginx видит реальные внешние IP. В логе уже был внешний `40.116.73.219`, а не `192.168.100.1`.
- IPBan запущен как служба и автозапускается.
- Уже забанен реальный IP `87.107.102.195`: он дернул bad-path 6 раз за несколько секунд.

Где что лежит на Win11:

```text
C:\nginx\conf\nginx.conf
C:\edge-proxy\logs\access.log
C:\edge-proxy\logs\nginx-error.log
C:\IPBanCustomLogs\nginx-badpaths.log
C:\IPBanCustomLogs\nginx-limit.log
C:\edge-proxy\logs\edge-ban-monitor.log
C:\Program Files\IPBan\
```

Автозапуск:

```text
\Portfolio\EdgeNginxStart
\Portfolio\EdgeNginxWatchdog
\Portfolio\EdgeBanMonitor
```

Текущие правила:

```text
bad-path ban: 5 событий за 10 минут
rate-limit: 10 r/s, burst 10
IPBan ban time: 1 сутки
whitelist: локальные сети + 31.25.31.72
```

Плохие пути сейчас отсекаются/банятся:

```text
/.env
/wp-login.php
/xmlrpc.php
/wp-admin
/wp-content
/phpmyadmin
/vendor/phpunit
/boaform
/cgi-bin
/adminer
/setup.php
/config.php
/tplus/ajaxpro
*.jsp
*.action
*.do
```

Важный момент на будущее: сертификаты я скопировал с Ubuntu/Hestia на Win11. Сейчас HTTPS работает, но автообновление сертификатов для Win11 еще отдельно надо будет настроить, иначе после истечения текущих сертификатов HTTPS начнет ругаться. Это следующий аккуратный шаг.

Источники по использованным компонентам: Nginx official download `https://nginx.org/en/download.html`, IPBan config/ban.txt docs `https://github.com/DigitalRuby/IPBan/wiki/Configuration` и `https://github.com/DigitalRuby/IPBan/wiki/Force-Ban-or-Unban`.