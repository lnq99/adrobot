# Adrobot — обёртка над API Keitaro

Обёртка над Admin API [Keitaro](https://keitaro.io/) (трекер / конструктор
ссылок), сделанная для тестового задания Adrobot. Две части:

1. **Создание кампании** — по `name`, `geo_code`, `offer_id` создаёт кампанию
   с двумя потоками (гео → Google и выбранный оффер), используя заранее
   настроенные домен / группу / источник.
2. **Редактор кампании** — добавление/удаление офферов в существующей кампании
   с пересчётом долей, черновик/публикация (push/cancel), возврат (bring-back),
   двусторонняя синхронизация с Keitaro (офферы, удалённые или добавленные прямо
   в трекере) и закреплённые доли (pinned weights).

> Стек: бэкенд — **FastAPI + SQLAlchemy 2.0 + Alembic + Postgres**;
> фронтенд — SPA на **React + TypeScript (Vite)**.

## Демо

<!-- ВСТРОЕННЫЙ ПЛЕЕР — GitHub рисует <video>-плеер, когда на отдельной строке
     стоит ссылка на ассет, размещённый на GitHub. Как её получить (локально
     сгенерировать нельзя):
       1. Запушить репозиторий на GitHub.
       2. На GitHub открыть новый Issue (или PR), перетащить
          `frontend/e2e/dual-demo-1080.mp4` в поле комментария и дождаться загрузки.
       3. Скопировать полученную ссылку `https://github.com/user-attachments/assets/<id>`.
       4. Вставить её на пустой строке ниже — одна «голая» ссылка, отдельной строкой.
          Сам Issue отправлять не нужно.
     Примечания: лимит загрузки ~10 МБ (файл весит 1.6 МБ); плеер отображается
     только на github.com (не в локальном предпросмотре/VS Code); GitHub показывает
     кнопку воспроизведения (автовоспроизведения нет). После этого запасную
     миниатюру ниже можно удалить. -->

<!-- ⬇ вставьте ссылку на видео GitHub на пустой строке прямо ниже ⬇ -->


▶️ **[Полное видео — прямая ссылка](https://pub-56a06514013f448db8c808889cc73bff.r2.dev/dual-demo-1080.mp4)** · запись в две панели: слева SPA Adrobot управляет **реальным** стендом Keitaro, а справа эмулятор KT реагирует вживую — создание кампании → автопересчёт долей → закрепление %, добавление офферов, **возврат (локально)** и **обратная синхронизация** (оффер, удалённый прямо в Keitaro и обнаруженный при обновлении).

<!-- Запасная миниатюра (отображается везде; клик → полное видео). Удалите, когда встроите плеер выше. -->
[![Демо Adrobot — слева SPA управляет реальным стендом Keitaro, справа эмулятор KT реагирует вживую](docs/assets/dual-demo-preview.png)](https://pub-56a06514013f448db8c808889cc73bff.r2.dev/dual-demo-1080.mp4)

## Статус

Реализовано. Бэкенд: FastAPI + SQLAlchemy + Alembic, все 46 сервисных/API-тестов
проходят (включая property/fuzz-набор из 500 случаев на математику долей).
Фронтенд: SPA на React + TypeScript (Vite), разворачивается на GitHub Pages.

## Документация

| Файл | Что это |
|------|---------|
| [`docs/task-ru.md`](./docs/task-ru.md) | Исходное задание (RU) |
| [`docs/api-reference.md`](./docs/api-reference.md) | **Проверенный** справочник API тест-стенда |
| [`docs/test-stand-ru.md`](./docs/test-stand-ru.md) | Заметки по доступу к тест-стенду (эмулятору) |
| [`docs/admin-api.openapi.json`](./docs/admin-api.openapi.json) | OpenAPI-спецификация Keitaro Admin API |
| [`docs/superpowers/specs/2026-11-26-adrobot-design.md`](./docs/superpowers/specs/2026-11-26-adrobot-design.md) | Спецификация дизайна |
| [`docs/superpowers/plans/2026-11-26-adrobot-implementation.md`](./docs/superpowers/plans/2026-11-26-adrobot-implementation.md) | План реализации (TDD) |

## Запуск

### 1. База данных (Postgres через Docker)

```bash
docker compose up -d
```

> Если локальный порт 5432 занят, задайте `PG_PORT` в `docker-compose.yml` и
> обновите `DATABASE_URL` в `backend/.env` соответственно.

### 2. Бэкенд

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # вставьте свой Keitaro Api-Key
alembic upgrade head            # применить миграции
uvicorn app.main:app --reload   # http://localhost:8000
```

### 3. Фронтенд

```bash
cd frontend
npm install
cp .env.example .env            # VITE_API_URL=http://localhost:8000
npm run dev                     # http://localhost:5173
```

### Тесты

```bash
cd backend && . .venv/bin/activate && pytest
```

## Фронтенд на GitHub Pages

Собранный SPA живёт на [`lnq99.github.io/adrobot`](https://lnq99.github.io/adrobot),
а бэкенд каждый пользователь запускает у себя локально. Браузер резолвит
`localhost` на машине пользователя, поэтому страница с Pages обращается к
`http://localhost:8000` — то есть к вашему собственному бэкенду.

- `http://localhost` считается доверённым источником, поэтому запрос с HTTPS-страницы
  на HTTP-localhost браузеры не блокируют (HTTPS на бэкенде не нужен).
- Origin Pages (`https://lnq99.github.io`, без пути) уже добавлен в `CORS_ORIGINS`.
- Если Chrome заблокирует preflight по Private Network Access, бэкенду нужно вернуть
  заголовок `Access-Control-Allow-Private-Network: true` (добавляется при
  необходимости).

## Часть 1 / Часть 2

- Вкладка **Create**: название + страны + оффер → кампания с 2 потоками
  (гео→Google, оффер).
- Вкладка **Editor**: выбрать кампанию → Fetch Streams → добавить/удалить/закрепить
  офферы, Push/Cancel. Жёлтый = не опубликовано; серый = удалён (подсказка на бейдже
  показывает, удалён он локально или в Keitaro).

## Как использовались ИИ-агенты

Проект разработан с помощью Claude Code по спек-ориентированному процессу
(брейншторм → спецификация → план → TDD). Итоговая спецификация и план реализации
лежат в [`docs/superpowers/`](./docs/superpowers); инструкции агента для проекта —
в [`CLAUDE.md`](./CLAUDE.md).

ИИ-агенты также использовались, чтобы:

- **Написать тесты** — набор pytest на бэкенде (46 сервисных/API-тестов, TDD) и
  end-to-end браузерные тесты на Playwright
  ([`frontend/e2e/`](./frontend/e2e)), которые гоняют реальный SPA против
  демо-бэкенда.
- **Снять видео-скринкаст** — демо в две панели [выше](#демо) генерируется
  Playwright-харнессом
  ([`frontend/e2e/dual-record.dual.ts`](./frontend/e2e/dual-record.dual.ts)):
  он записывает SPA Adrobot и живой эмулятор Keitaro как две панели, затем
  склеивает их в одно видео 1080p через ffmpeg
  ([`frontend/scripts/merge-lr.sh`](./frontend/scripts/merge-lr.sh)) — с
  подписями, курсором и анимацией кликов.
