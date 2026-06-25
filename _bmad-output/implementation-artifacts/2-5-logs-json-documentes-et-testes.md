# Story 2.5: Logs JSON documentes et testes

Status: done

## Story

En tant que mainteneur,
je veux que le format de logs JSON soit teste et documente,
afin de pouvoir brancher l'application sur des outils d'exploitation sans deviner les champs disponibles.

## Acceptance Criteria

1. Le formatter JSON est couvert par des tests unitaires.
2. Les champs standards `timestamp`, `level`, `logger` et `message` restent stables.
3. Les champs operationnels `event`, `job_id`, `status`, `error_code` et `platform` sont couverts.
4. Le README documente le format de logs, les principaux evenements et `LOG_LEVEL`.
5. Les controles qualite passent.

## Tasks / Subtasks

- [x] Ajouter des tests pour `JsonFormatter` (AC: 1, 2, 3)
- [x] Documenter les logs JSON dans le README (AC: 4)
- [x] Ajouter la story au planning et au suivi sprint (AC: 5)
- [x] Executer les controles qualite (AC: 5)

## Dev Notes

- Le formatter JSON existait deja dans `app/core/logging.py`.
- Cette story stabilise le contrat observable sans modifier le comportement runtime.
- Les logs sortent sur stdout pour rester compatibles Docker/Compose et collecteurs de logs.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `XDG_CACHE_HOME=/tmp/mediaforgetool-uv-cache rtk uv run ruff check .` -> all checks passed
- `rtk .venv/bin/python -m pytest tests/test_logging.py -q` -> 2 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk .venv/bin/python -m pytest -q` -> 45 passed, 1 pytest-asyncio deprecation warning under Python 3.14

### Completion Notes List

- Ajout de tests unitaires du formatter JSON.
- README mis a jour avec les champs standards, champs operationnels et evenements courants.
- Aucun changement runtime sur le pipeline media.

### File List

- `tests/test_logging.py`
- `README.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/2-5-logs-json-documentes-et-testes.md`

## Change Log

- 2026-06-02: Story 2.5 creee, implementee et terminee.
