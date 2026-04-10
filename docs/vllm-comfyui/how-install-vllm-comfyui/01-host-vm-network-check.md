# 01. Host VM Network Check

Если проект на Ubuntu VM лежит не в `~/portfolio`, во всех следующих файлах замените этот путь на ваш реальный.

Стоп после выполнения этого файла и пришлите мне:

- Windows host IPv4;
- результат проверки `ComfyUI`;
- результат `curl` из Ubuntu VM;
- результат `curl` из контейнера backend.

## Цель шага

Понять, как Ubuntu VM и контейнер backend достучатся до `ComfyUI` и позже до `vLLM`, которые живут на хосте `Win11`.

## Где что выполняем

- `Win11 host`: PowerShell
- `Ubuntu VM`: bash
- `backend container`: команда через `docker compose exec backend ...`

## 1. Проверяем ComfyUI на Win11 host

Выполнить на `Win11 host` в PowerShell:

```powershell
hostname
ipconfig
netstat -ano | findstr :8188
curl.exe http://127.0.0.1:8188/
```

Что делаем:

- убеждаемся, что `ComfyUI` реально слушает порт `8188`;
- фиксируем IPv4 адрес Windows host;
- проверяем, что локально на host `ComfyUI` отвечает.

Что сохранить:

- IPv4 адрес Windows host;
- строку из `netstat` по порту `8188`.

## 2. Проверяем сеть из Ubuntu VM до Win11 host

Выполнить в `Ubuntu VM`:

```bash
hostname
hostname -I
ip route
ping -c 2 <WIN_HOST_IP>
curl -I http://<WIN_HOST_IP>:8188/
```

Что делаем:

- проверяем, что VM видит host по сети;
- проверяем, что `ComfyUI` доступен из самой VM.

Если `ping` проходит, а `curl` нет:

- пока не чините ничего сами;
- просто пришлите мне вывод команд.

## 3. Проверяем доступ из backend контейнера

Выполнить в `Ubuntu VM`, в корне проекта:

```bash
cd ~/portfolio
docker compose exec backend curl -fsS http://<WIN_HOST_IP>:8188/ > /tmp/comfyui_check.html && echo "COMFYUI_OK"
docker compose exec backend sh -lc "wc -c /tmp/comfyui_check.html && rm -f /tmp/comfyui_check.html"
```

Что делаем:

- убеждаемся, что backend контейнер достучится до Windows host, а не только сама VM.

## Критерий успеха

Успешным считаем шаг, если:

- `ComfyUI` отвечает на host;
- `Ubuntu VM` достучалась до `http://<WIN_HOST_IP>:8188/`;
- backend контейнер тоже достучался до этого адреса.

## Что прислать мне после выполнения

Пришлите:

1. Windows host IPv4
2. Вывод `curl -I http://<WIN_HOST_IP>:8188/` из VM
3. Вывод `COMFYUI_OK` из backend контейнера
