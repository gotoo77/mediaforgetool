# Story 3.4: Protection des jobs pauses contre la purge

Status: done

## Story

En tant qu'utilisateur,
je veux qu'un job mis en pause ne soit pas supprime par les controles de nettoyage d'historique,
afin de pouvoir reprendre volontairement un traitement suspendu sans le perdre par erreur.

## Acceptance Criteria

1. `DELETE /api/jobs/{job_id}` refuse les jobs `paused`.
2. `DELETE /api/jobs` ignore les jobs `paused` comme les autres jobs actifs ou protegés.
3. L'interface n'affiche plus l'action Supprimer pour un job `paused`.
4. Le README precise que la purge globale ignore les jobs actifs ou pauses.
5. Les tests API couvrent suppression unitaire et purge globale pour `paused`.
6. Les controles qualite passent.

## Tasks / Subtasks

- [x] Proteger `paused` dans l'ensemble des statuts non supprimables (AC: 1, 2)
- [x] Ajouter les tests API de regression (AC: 5)
- [x] Aligner les actions d'historique du navigateur (AC: 3)
- [x] Documenter le comportement public dans le README (AC: 4)
- [x] Ajouter la story au planning et au suivi sprint (AC: 6)
- [x] Executer les controles qualite cibles et complets (AC: 6)

## Dev Notes

- `paused` reste volontairement reprenable via `POST /api/jobs/{job_id}/resume`.
- Avant cette story, la purge globale des jobs inactifs pouvait supprimer un job pause, et l'interface affichait aussi Supprimer pour ce statut.
- Les jobs `failed` et `interrupted` restent supprimables afin de permettre un nettoyage explicite des erreurs.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_jobs_api.py -q` -> 26 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk uv run ruff check app/api/routes/jobs.py tests/test_jobs_api.py` -> all checks passed
- `rtk uv run pytest -q` -> 65 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk uv run ruff check .` -> all checks passed

### Completion Notes List

- Les jobs `paused` sont maintenant proteges par les endpoints de suppression.
- La purge globale les compte dans `active_jobs_skipped`.
- L'historique navigateur masque Supprimer pour `paused` tout en gardant Reprendre.

### File List

- `README.md`
- `app/api/routes/jobs.py`
- `app/static/app.js`
- `tests/test_jobs_api.py`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/3-4-protection-des-jobs-pauses-contre-la-purge.md`

## Change Log

- 2026-06-15: Story 3.4 creee, implementee et terminee.
