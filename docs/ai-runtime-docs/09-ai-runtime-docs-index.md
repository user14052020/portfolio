# 09. AI Runtime Docs Index

See also: [10-models-in-use.md](./10-models-in-use.md)

Этот файл служит точкой входа в runtime-документацию по AI-сервисам проекта.

## Файлы

1. [07-vllm-runtime-reference.md](./07-vllm-runtime-reference.md)
   Детально про `vLLM`: где установлен, как запускается, какая модель используется, какие env нужны, как проверять доступность и что считается нормальным поведением.

2. [08-comfyui-runtime-reference.md](./08-comfyui-runtime-reference.md)
   Детально про `ComfyUI`: где установлен, как запускается после переноса в `C:\dev\ComfyUI`, какие порты используются, как устроен доступ из Ubuntu VM и где сейчас искать причину `400 Bad Request`.

3. [06-autostart-map.md](./06-autostart-map.md)
   Карта автозапуска: что должно стартовать автоматически после reboot, где лежат startup scripts и где хранятся логи.

## Когда какой файл открывать

- Если нужно понять текстовый AI-контур, открывайте `07`.
- Если нужно понять image generation-контур, открывайте `08`.
- Если нужно понять reboot/autostart/logging, открывайте `06`.

## Что дальше после этой документации

Следующий рабочий разбор по проекту:

- разобрать `ComfyUI 400 Bad Request` на `/prompt`;
- отдельно причесать warning в логах `vLLM` про `WSL localhost`;
- после этого вернуться к качеству stylist responses и routing.
