# Браузерная версия: Godot / WebAssembly

Это настоящая сборка исходной Godot-игры в WebAssembly, а не JavaScript-переписывание. `scripts/build_web.py` использует Godot **4.4.1** и официальные single-thread web export templates той же версии. Нужны WebGL 2 и WebAssembly. GDScript, мир, бой, HUD и сохранения исходной игры сохранены.

Первый запуск скачивает архив официальных export templates (~1.15 GiB); далее используется кэш `.state/web-tools`. Экспорт в `web/dist` не коммитится; `build.json` записывает версию и SHA-256 собранного `.wasm`. Путь к установленному Godot можно задать через `GODOT_BIN`. Сохранения идут в Godot user:// через IndexedDB; после записи вызывается `force_fs_sync()`.

Источники: [Godot 4.4 Web export](https://docs.godotengine.org/en/4.4/tutorials/export/exporting_for_web.html), [HTML shell](https://docs.godotengine.org/en/4.4/tutorials/platform/web/customizing_html5_shell.html), [JavaScriptBridge](https://docs.godotengine.org/en/4.4/classes/class_javascriptbridge.html).

## Запуск

Нужны Docker Desktop, Python 3 с venv и зависимости существующего backend; WASM дополнительно требует Godot 4.4.1. В текущем рабочем пространстве всё установлено.

Из каталога этой ветки:

```sh
./scripts/start_web.sh
# Открыть http://127.0.0.1:8081
```

Команда запускает общий persistent backend через `scripts/start.sh --no-game`, затем браузерный сервер. В worktree общий репозиторий определяется через `git --git-common-dir`: отдельный worker и другой набор кошельков не создаются. Сервер слушает только 127.0.0.1. Повторный запуск на том же порту сообщает, что сервер уже работает. Ctrl+C завершает frontend-сервер; backend/worker и данные сохраняются.

Если backend уже запущен, достаточно `./scripts/web.sh`. Порт меняется через `--port`; backend по умолчанию 8787, можно передать `--backend-port`. Не открывайте index.html через file://: нужен same-origin proxy `/api/*`.

## Игровой сценарий

1. Начать/продолжить кампанию. WASD, мышь + ЛКМ, Space, E, Q, I и R.
2. Синий портал в деревне открывает серверное Испытание Клятвы. Защищайтесь от heavy, отдыхайте при нехватке выносливости, атакуйте в остальные ходы.
3. Победа ставит выдачу в очередь настоящего worker. В RGB-предметах дождитесь подтверждения владения.
4. Экипируйте меч: реальный урон персонажа меняется с 22 на 52 при активном серверном lease.
5. Выберите получателя **WASM B**, подтвердите передачу. Меч резервируется и снимается с экипировки.
6. После завершения переключитесь на **WASM B** и экипируйте тот же экземпляр/asset_id. У A он больше недоступен.

Обычные профили называются `WASM A/B`. Это новые браузерные аккаунты, **не** существующие нативные «Игрок A/B». Профили различаются UUID; имя само по себе не доказывает личность или владение. Нативный меч #4 не переносится автоматически и остаётся у обычного «Игрок A».

Ключи каждого RGB-кошелька хранит существующий локальный Python-сервис; браузер получает только API bearer credentials. Никаких mainnet, новых RGB-версий или fallback на mock. Стек остаётся `rgb-lib==0.3.0b7` / RGB v0.11.1-rc.11. При отключении backend или кошельков интерфейс показывает ошибку, lease истекает, урон возвращается к локальному оружию. Обычное золото и предметы кампании остаются локальными игровыми данными.

Сохранения и профили привязаны к origin (схема + hostname + порт): используйте один адрес. Удаление site data теряет браузерные credentials; восстановления входа в этой версии нет. Не импортируйте credentials других проектов. Установленный на сервере backend по-прежнему обеспечивает idempotency, серверный бой, подлинность зарегистрированных UDA и проверку кошельков; клиент не выдаёт награды из локального сохранения.

## Проверки

Фактически выполнено 2026-10-17:

- 23 существующих backend tests — PASS (один сторонний deprecation warning).
- 6 static/proxy tests — PASS: assets/MIME, защита приватных путей, config без credentials, auth forwarding, Origin и backend offline 503.
- Полный **HTTP proxy + real RGB** сценарий — PASS: серверная победа → один UDA → экипировка A → настоящая передача → тот же asset_id → запрет использования A → экипировка B. Также проверены повтор награды/передачи, запрет двойной передачи и чужого asset_id. Доказательства: [web-api-webassembly.json](evidence/web-api-webassembly.json). Этот тест не является визуальной проверкой браузера.
- Godot import + release web export прошли без ошибок; валидирован заголовок настоящего `.wasm`, размер 43,699,190 bytes.
- Godot headless smoke: connectivity, quests, chests, shrine, movement, collision, melee/ranged, dodge, boss, loot, equipment, save/load, death/respawn — PASS.
- Chromium начальный probe до запрета ручного Browser Use загрузил WASM и настоящий игровой мир, зарегистрировал отдельные тестовые профили и подключился к реальному backend. Дальнейший E2E остановился на ошибке тестового запуска Continue без сохранения; fallback теста исправлен. Ошибка растягивания canvas исправлена настройкой canvasResizePolicy=0, экспорт повторён. Эти последние исправления повторно в браузере не проверены.

**Ручная проверка интерфейса не пройдена:** Computer Use / Chrome был отклонён системой разрешений по причине отказа пользователя. После отказа браузерная автоматизация остановлена; обход через другой браузер не применялся. HTTP/unit/headless Godot проверки выполнены отдельно и не подменяют ручной UI QA. Полный browser E2E `web/tests/browser.cjs` оставлен для последующего разрешённого запуска, его текущий итог не PASS.

Воспроизводимые команды из каталога ветки (backend должен работать):

```sh
python3 web/tests/test_server.py
python3 scripts/build_web.py
python3 scripts/web_regtest.py --label webassembly --url http://127.0.0.1:8081
```

HTTP regtest использует отдельные `is_test=true` профили; credentials сохраняет только в игнорируемом `.state/web-api-webassembly.json`, повторный запуск продолжает тот же reward/transfer. В evidence нет ключей/токенов. Тестовые игроки не появляются в списках обычных игроков.

Для полного browser E2E в отдельном терминале запустите `./scripts/web.sh --port 18081 --qa`, затем:

```sh
npm ci --prefix web
cd web
npx playwright install chromium
WEB_URL=http://127.0.0.1:18081 npm run test:browser
```

QA-флаг включает только тестовые профили и QA hooks, но не обход серверного боя или RGB. Без `--qa` hooks не активируются. Не используйте normal player origin для автоматических тестов.

Ограничения: desktop browser с клавиатурой/мышью; мобильное touch-управление не реализовано. Обмен предмет-на-предмет и внешние кошельки не добавлялись. Кошельки custodial, локальный regtest; это не production/web-hosting deployment. Нужна разрешённая полная повторная браузерная и ручная UI проверка.
