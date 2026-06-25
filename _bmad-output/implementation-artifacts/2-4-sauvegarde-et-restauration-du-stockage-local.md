# Story 2.4: Sauvegarde et restauration du stockage local

Status: done

## Story

En tant que mainteneur,
je veux disposer d'un script documente pour sauvegarder et restaurer SQLite et les sorties retenues,
afin de pouvoir deplacer ou recuperer une instance self-hosted sans manipulations manuelles fragiles.

## Acceptance Criteria

1. Un script permet de creer une archive contenant `storage/mediaforgetool.db` et `storage/jobs`.
2. La sauvegarde SQLite utilise l'API `sqlite3.backup` plutot qu'une simple copie brute.
3. La restauration refuse de remplacer un stockage non vide sans option explicite.
4. L'extraction d'archive protege contre les chemins dangereux.
5. Le README documente les commandes de sauvegarde et restauration.
6. Les tests couvrent creation, restauration et refus de remplacement implicite.
7. Les controles `rtk uv run ruff check .` et `rtk uv run pytest -q` passent.

## Tasks / Subtasks

- [x] Ajouter `scripts/storage_backup.py` avec commandes `create` et `restore` (AC: 1, 2, 3, 4)
- [x] Ajouter des tests unitaires du script (AC: 6)
- [x] Documenter le runbook backup/restore dans le README (AC: 5)
- [x] Executer les controles qualite (AC: 7)

## Dev Notes

- La restauration doit etre faite application arretee pour eviter une connexion SQLite active sur l'ancien fichier.
- Les sorties terminees sont sous `storage/jobs`; les temporaires `temp/jobs` restent exclus des sauvegardes.
- Les secrets/cookies restent hors archive de sauvegarde par defaut.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `XDG_CACHE_HOME=/tmp/mediaforgetool-uv-cache rtk uv run ruff check .` -> all checks passed
- `rtk .venv/bin/python -m pytest tests/test_storage_backup.py -q` -> 3 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk .venv/bin/python -m pytest -q` -> 43 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `XDG_CACHE_HOME=/tmp/mediaforgetool-uv-cache timeout 20s rtk uv run pytest -q` -> timed out after printing four progress dots in this sandbox; direct `.venv` pytest completed successfully

### Completion Notes List

- Ajout d'un script CLI standard-library pour sauvegarder/restaurer le stockage MediaForgeTool.
- Ajout de tests couvrant archive, restauration et garde `--force`.
- README mis a jour avec les commandes de runbook.

### File List

- `scripts/storage_backup.py`
- `tests/test_storage_backup.py`
- `README.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/2-4-sauvegarde-et-restauration-du-stockage-local.md`

## Change Log

- 2026-06-02: Story 2.4 creee, implementee et terminee.
