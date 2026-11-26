# KT Emulator — учебный стенд

> Админка: <https://keitaro-for-tests.etolegko.com/admin/#!/docs/>
> Сводка проверенных вызовов и полей — в [`api-reference.md`](./api-reference.md).

## Что это

Учебный стенд: он отвечает как Admin API трекера Keitaro в той части, что нужна
для задания. Пишите обёртку так, будто ходите в настоящий Keitaro. Поля запросов
и ответов те же, что в [документации Admin API](https://admin-api.docs.keitaro.io/).

## Как ходить

- Войти на стенд можно через **GitHub**: логином станет ваш ник.
- Адрес API: `https://keitaro-for-tests.etolegko.com/admin_api/v1`.
- Ключ — в заголовке `Api-Key`; свой ключ увидите по кнопке «API ключ» вверху.
- Вы видите только свои кампании.
- Ссылка на кампанию в админке: `…/admin/#!/campaign.editor/<id>`.

```bash
curl -H "Api-Key: <ваш ключ>" \
  https://keitaro-for-tests.etolegko.com/admin_api/v1/offers
```

```bash
# поток «страна → Google»
curl -X POST https://keitaro-for-tests.etolegko.com/admin_api/v1/streams \
  -H "Api-Key: <ваш ключ>" -H "Content-Type: application/json" \
  -d '{"campaign_id": 1, "name": "Geo GM", "type": "regular", "schema": "redirect",
       "action_type": "http", "action_payload": "https://google.com",
       "filters": [{"name": "country", "mode": "accept", "payload": ["GM"]}]}'
```

```bash
# поток с офферами
curl -X POST https://keitaro-for-tests.etolegko.com/admin_api/v1/streams \
  -H "Api-Key: <ваш ключ>" -H "Content-Type: application/json" \
  -d '{"campaign_id": 1, "name": "Офферы", "type": "default", "schema": "landings",
       "offers": [{"offer_id": 18001, "share": 100, "state": "active"}]}'
```

## Что поддержано

| Метод + путь | Описание |
|--------------|----------|
| `GET /campaigns` | Ваши кампании, новые сверху. Параметры `offset` и `limit`. |
| `POST /campaigns` | Создать кампанию. Обязательно `name`; `alias` придумается сам, если не задан. |
| `GET /campaigns/{id}` | Одна кампания. |
| `PUT /campaigns/{id}` | Изменить кампанию: меняются только присланные поля. |
| `DELETE /campaigns/{id}` | Удалить кампанию вместе с потоками. **Архива нет.** |
| `POST /campaigns/{id}/enable` · `/disable` | Включить / выключить. |
| `GET /campaigns/{id}/streams` | Потоки кампании по порядку `position`. |
| `POST /streams` | Создать поток. Обязательны `campaign_id` и `name`. |
| `GET /streams/{id}` | Один поток с фильтрами и офферами. |
| `PUT /streams/{id}` | Изменить поток. `offers` заменяет состав целиком, `filters` — фильтры целиком. |
| `DELETE /streams/{id}` | Удалить поток. |
| `POST /streams/{id}/enable` · `/disable` | Включить / выключить. |
| `GET /offers` · `/offers/{id}` | Офферы. Только чтение. |
| `GET /groups?type=campaigns` | Группы кампаний. Только чтение. |
| `GET /domains` | Домены. Только чтение. |
| `GET /traffic_sources` | Источники. Только чтение. |

## Что уже есть на стенде

170 офферов, домен (**id 1813**), группа кампаний `FORTESTS` (**id 10332**),
источник `FORTESTS` (**id 836**). Каталог общий и только для чтения: создать или
изменить оффер, группу, домен, источник нельзя.

## Чего нет

- Кликов и статистики: ссылка кампании никуда не ведёт.
- Лендингов, триггеров, постбэков, отчётов, архива удалённого.
- Справочников `/stream_filters`, `/streams_actions`, `/stream_types`, `/stream_schemas`.
- Остальных путей Admin API: на них стенд ответит ошибкой.

## Журнал

Раздел «Журнал» показывает каждый запрос вашей обёртки к API: время, путь, тело,
код ответа. **Проверяющий видит тот же журнал.**
