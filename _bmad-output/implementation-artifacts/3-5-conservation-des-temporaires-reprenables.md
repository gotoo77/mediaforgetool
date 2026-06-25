# Story 3.5: Conservation des temporaires reprenables

Status: done

## Story

En tant qu'utilisateur,
je veux que le nettoyage automatique conserve les dossiers temporaires des jobs pauses ou interrompus,
afin qu'une reprise volontaire ne perde pas les donnees partielles encore utiles.

## Acceptance Criteria

1. `CleanupService.cleanup_now()` ne supprime pas les dossiers temporaires des jobs `paused`.
2. `CleanupService.cleanup_now()` ne supprime pas les dossiers temporaires des jobs `interrupted`.
3. Les dossiers temporaires anciens non proteges restent supprimables.
4. Le README mentionne que le nettoyage preserve les jobs pauses ou interrompus reprenables.
5. Les tests couvrent la conservation des temporaires reprenables et le nettoyage des temporaires non proteges.
6. Les controles qualite passent.

## Tasks / Subtasks

- [x] Identifier les statuts dont les temporaires doivent etre preserves (AC: 1, 2)
- [x] Passer les IDs proteges au balayage des dossiers temporaires (AC: 1, 2, 3)
- [x] Ajouter un test de regression du service cleanup (AC: 5)
- [x] Documenter le comportement public dans le README (AC: 4)
- [x] Ajouter la story au planning et au suivi sprint (AC: 6)
- [x] Executer les controles qualite cibles et complets (AC: 6)

## Dev Notes

- Le runner preserve deja les dossiers temporaires des jobs `paused` et `interrupted`.
- Avant cette story, le cleanup automatique pouvait supprimer ces dossiers uniquement sur l'age du repertoire.
- Les temporaires de jobs `failed` et les dossiers orphelins restent nettoyables.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_cleanup_service.py -q` -> 1 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk uv run ruff check app/services/cleanup_service.py tests/test_cleanup_service.py` -> all checks passed
- `rtk uv run pytest -q` -> 66 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk uv run ruff check .` -> all checks passed

### Completion Notes List

- Le cleanup calcule les IDs de jobs avec statuts proteges avant de nettoyer `temp_dir`.
- Les dossiers `paused` et `interrupted` ages sont conserves.
- Les dossiers `failed` et orphelins ages restent supprimes.

### File List

- `README.md`
- `app/services/cleanup_service.py`
- `tests/test_cleanup_service.py`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/3-5-conservation-des-temporaires-reprenables.md`

## Change Log

- 2026-06-15: Story 3.5 creee, implementee et terminee.
