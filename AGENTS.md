# Инструкции для проекта

- Все пользовательские сообщения, документация и подписи интерфейса — на русском языке.
- Neutral tone is always 0, never 5.
- Pinyin is always numeric-tone pinyin в нижнем регистре.
- Canonical ü representation is v.
- Не добавлять CDN и сетевые зависимости в карточки: колода обязана работать офлайн.
- No CDN/network dependency inside cards.
- Do not replace Anki's SRS.
- Do not regenerate random model/deck IDs.
- Do not break existing TSV data.
- `data/radicals.tsv` должен содержать только графемы из упражнений «Выпишите иероглифы, в которых встречаются данные графемы, и переведите их»: 9/28/22/35/28/13 групп для уроков 1–6.
- Структура колод: `Китайский для русскоязычных::Слова::Урок N` и `Китайский для русскоязычных::Ключи::Урок N`; все они собираются в один `dist/chinese-ru.apkg`.
- Не объединять колоды ключей разных уроков в одну подколоду и не менять их стабильные deck ID.
- Не коммитить `node_modules`, `.venv`, `assets/generated` и `dist/`. Готовые колоды публикуются только в `decks/` через `make decks` после успешных `make test` и проверки пакетов.
- После изменений запускать `make test` и, если затронута сборка, `make build`.
