# Story 2.8: Correlation request id

Status: done

## Story

En tant que mainteneur,
je veux que chaque reponse expose un `X-Request-ID` et que les logs JSON puissent porter ce meme identifiant,
afin de correler plus facilement les incidents entre reverse proxy, application et logs.

## Acceptance Criteria

1. Chaque reponse HTTP expose un header `X-Request-ID`.
2. Une valeur entrante `X-Request-ID` printable et courte est preservee.
3. Une valeur est generee quand le header entrant est absent ou invalide.
4. Le formatter JSON inclut `request_id` quand un identifiant est present dans le contexte.
5. Les erreurs applicatives precoces, dont limite de body, conservent aussi `X-Request-ID`.
6. Le README documente le header et son lien avec les logs.
7. Les controles qualite passent.

## Tasks / Subtasks

- [x] Ajouter un contexte request id au logging (AC: 4)
- [x] Ajouter un middleware FastAPI `X-Request-ID` (AC: 1, 2, 3, 5)
- [x] Ajouter des tests de header et de formatter JSON (AC: 1, 2, 4, 5)
- [x] Documenter `X-Request-ID` dans README (AC: 6)
- [x] Ajouter la story au planning et au suivi sprint (AC: 7)
- [x] Executer les controles qualite (AC: 7)

## Dev Notes

- L'identifiant entrant est preserve s'il reste printable et limite a 128 caracteres.
- Les logs utilisent un `ContextVar` pour eviter de passer manuellement `request_id` dans chaque appel logger.
- Les jobs de fond peuvent continuer a utiliser `job_id`; `request_id` couvre surtout la surface HTTP.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `XDG_CACHE_HOME=/tmp/mediaforgetool-uv-cache rtk uv run ruff check .` -> all checks passed
- `rtk .venv/bin/python -m pytest tests/test_request_id.py tests/test_logging.py -q` -> 6 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk .venv/bin/python -m pytest -q` -> 53 passed, 1 pytest-asyncio deprecation warning under Python 3.14

### Completion Notes List

- Ajout de `ContextVar` request id dans `app/core/logging.py`.
- Ajout d'un middleware FastAPI `X-Request-ID`.
- Ajout de tests de generation, preservation et erreur 413.
- README mis a jour pour la correlation logs/reponses.

### File List

- `app/core/logging.py`
- `app/main.py`
- `tests/test_logging.py`
- `tests/test_request_id.py`
- `README.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/2-8-correlation-request-id.md`

## Change Log

- 2026-06-02: Story 2.8 creee, implementee et terminee.
