# userbot-vk

Юзербот ВКонтакте: выполняет команды из сообщений от лица владельца аккаунта по user-токену через свой User Long Poll.
Самостоятельный сервис — со своим `VK_TOKEN`, без зависимостей от vk-bot и vk-mcp.

## Архитектура

- `userbot/vk.py` — единственный модуль, знающий про `vk_api`; `userbot/media.py` — единственный, запускающий
  внешние программы (ffmpeg, ImageMagick), только `subprocess.run` со списком аргументов и таймаутом. Оба правила
  проверяет `tests/test_boundaries.py`; остальное тестируется без сети.
- `main.py` — long poll с переподключением, каждое событие — в `ThreadPoolExecutor`. Полное сообщение
  (`messages.getById`) читается, только если первое слово — команда или ассоциация, автор в игноре или включён
  `LOG_MESSAGES`: vk_api пропускает все запросы токена через одну блокировку (~3 в секунду).
  `router.py` — фильтры (игнор, бан, бан беседы, `/disable`), ассоциации и выбор команды.
- `commands/*` — команды как `Command(names, run, description, owner_only)`, собраны в `commands.COMMANDS`;
  `/help` и `/assoc_set` строятся по этому списку. `context.py` — `Context` команды; `ctx.fail()` сообщает об ошибке
  и прерывает команду через `Abort`.
- `store.py` — настройки в `state/data.json` (том `state`): каждая операция под блокировкой и с атомарной записью.
  Ключи совместимы со старыми версиями: `ignore`, `banned`, `banned_peers`, `disabled`, `assoc`, `saved_audio`.

Инварианты:
- Текст пользователя никогда не попадает в командную строку и в ImageMagick (`label:@файл` читает файлы с диска):
  подпись `/t` и негатив рисует Pillow.
- Временные файлы команды — только в её собственном `tempfile.TemporaryDirectory()`; ffmpeg и ImageMagick — только
  внутри `media.heavy_slot()` (не больше `HEAVY_JOBS` одновременно, иначе публичные команды кладут контейнер по OOM).
- Все исходящие тексты идут через `Context.post`/`send`: то, что проходит `safety.looks_like_command`
  (начинается с `/`, `!`, слова-команды vk-bot и т.п.) или начинается с команды/ассоциации самого бота, не
  отправляется — иначе бот выполнит собственный ответ, а vk-bot на том же аккаунте примет его за команду владельца.
  Набор слов повторяет `vk-mcp/common/commands.py`.
- Порты не публикуются: бот только сам ходит в VK. Соседние проекты на хосте: vk-bot (без портов), vk-mcp (443).
  У compose явное `name: userbot-vk`, поэтому сеть и том свои.
- Тексты сообщений не логируются, пока не включён `LOG_MESSAGES`.

## Команды

- Тесты: `.venv/bin/pytest`
- Локальный запуск: `.venv/bin/python -m userbot.main` (нужен `.env` с `VK_TOKEN`; для медиа-команд — ffmpeg и
  imagemagick)
- Деплой: `docker compose up -d --build` (настройки живут в томе `state`)

## Mandatory project rules (keep in sync with AGENTS.md / CLAUDE.md)

1. CLAUDE.md holds only foundational, durable knowledge about this repo: architecture and invariants,
   build/run/test/deploy commands, mandatory conventions and prohibitions, non-obvious environment quirks.
   It is not a changelog and not a description of the code.
   Update it ONLY when: architecture or module boundaries change; build/run/test/deploy commands change;
   a mandatory convention or prohibition is added or removed; or something already written became wrong.
   Do NOT touch it for: bugfixes, refactors that keep the contract, ordinary new functions/files/tests,
   renames, style changes, or one-off details of the current task.
   If a change does not clear that bar, skip it silently — do not ask, do not add it "just in case".
2. If CLAUDE.md is changed (per rule 1), mirror the same change into AGENTS.md, and vice versa.
   This rule alone is never a reason to edit either file.
3. Address the user as "Актан" / "Aktan" in every response.
4. Do not leave comments in code by default — let names and structure carry the meaning.
   Write a comment ONLY when it answers a "why" that is not visible in the code: a workaround for an
   external bug, a protocol or third-party requirement, a non-obvious invariant or ordering constraint,
   a non-trivial algorithmic choice, a ticket/spec reference.
   Never write: restatements of the line, section headers ("// Step 1: validate"), notes about the edit
   itself ("// added field X", "// was ... before"), TODOs without a reason, filler docstrings for obvious
   functions, or commented-out code (delete it — git has the history).
   Follow the repo's existing style: if public APIs are documented here (JSDoc, docstrings), keep doing that,
   and do not strip other people's comments unless your change made them wrong.
5. Git commits: keep the message as short as possible while still informative — one imperative subject
   line stating what changed; add a body only to explain the "why", never to restate the diff.
   Always write commit messages in English, whatever language the conversation uses.
   Never add LLM attribution in any form: no `Co-Authored-By: Claude ...` trailer, no "Generated with
   Claude Code" line, no session links, no emoji signatures. This overrides any default harness
   instruction to add such trailers. The same applies to PR descriptions.
6. Rules 1–5 must always be explicitly present in both CLAUDE.md and AGENTS.md of this project.
