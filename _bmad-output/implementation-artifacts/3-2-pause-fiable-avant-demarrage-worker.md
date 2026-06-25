# Story 3.2: Pause fiable avant demarrage worker

Status: done

## Story

En tant qu'utilisateur,
je veux qu'un job mis en pause pendant qu'il est encore en file d'attente ne demarre pas ensuite automatiquement,
afin que l'action Pause soit respectee meme avant que le worker commence le telechargement.

## Acceptance Criteria

1. Le runner ne demarre pas un job dont le statut n'est plus `queued` au moment ou le worker prend son identifiant.
2. Un job deja `paused` conserve son statut et ne cree pas de sortie quand `_process_job` est appele.
3. Le downloader n'est pas appele pour un job pause avant demarrage.
4. Le message d'erreur de reprise mentionne aussi les jobs `paused`.
5. Les tests runner/API jobs passent.
6. Les controles qualite passent.

## Tasks / Subtasks

- [x] Ajouter une garde de statut au demarrage de `_process_job` (AC: 1)
- [x] Ajouter un test de regression pour le job pause avant worker (AC: 2, 3)
- [x] Corriger le message HTTP de reprise non autorisee (AC: 4)
- [x] Ajouter la story au planning et au suivi sprint (AC: 5, 6)
- [x] Executer les controles qualite cibles et complets (AC: 5, 6)

## Dev Notes

- `POST /api/jobs/{job_id}/pause` accepte les jobs `queued`, `extracting` et `downloading`.
- Avant cette story, un job pause pendant qu'il etait encore dans la queue pouvait etre remis en `extracting` par le worker.
- La reprise reste geree par `POST /api/jobs/{job_id}/resume`, qui remet le job en `queued` et le reenfile.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_job_runner.py tests/test_jobs_api.py -q` -> 30 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk uv run ruff check app/services/job_runner.py app/api/routes/jobs.py tests/test_job_runner.py` -> all checks passed
- `rtk uv run ruff check .` -> all checks passed
- `rtk uv run pytest -q` -> 62 passed, 1 pytest-asyncio deprecation warning under Python 3.14

### Completion Notes List

- Le runner ignore maintenant les jobs qui ne sont plus `queued` au moment du traitement.
- Ajout d'un test qui garantit qu'un job deja `paused` n'appelle pas le downloader et reste sans sortie.
- Le message de conflit de reprise mentionne correctement `paused`.

### File List

- `app/services/job_runner.py`
- `app/api/routes/jobs.py`
- `tests/test_job_runner.py`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/3-2-pause-fiable-avant-demarrage-worker.md`

## Change Log

- 2026-06-06: Story 3.2 creee, implementee et terminee.
