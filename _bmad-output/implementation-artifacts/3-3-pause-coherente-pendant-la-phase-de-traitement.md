# Story 3.3: Pause coherente pendant la phase de traitement

Status: done

## Story

En tant qu'utilisateur,
je veux que l'action Pause reste acceptee quand un job est en phase `processing`,
afin que les controles affiches dans l'interface correspondent au contrat API et que le fichier final ne soit pas publie apres une pause tardive.

## Acceptance Criteria

1. `POST /api/jobs/{job_id}/pause` accepte les jobs `processing`.
2. Le runner verifie explicitement l'etat `paused` apres le retour du downloader et avant publication du fichier final.
3. Un job mis en pause pendant `processing` reste `paused`, ne renseigne pas `output_path` et ne cree pas de sortie publiee.
4. Les tests API et runner couvrent cette regression.
5. Les controles qualite cibles passent.

## Tasks / Subtasks

- [x] Ajouter `processing` aux statuts pausables de l'API (AC: 1)
- [x] Ajouter une garde runner avant publication du fichier final (AC: 2, 3)
- [x] Ajouter les tests de regression API et runner (AC: 4)
- [x] Ajouter la story au planning et au suivi sprint (AC: 5)
- [x] Executer les controles qualite cibles (AC: 5)

## Dev Notes

- L'interface affichait deja le bouton Pause pour `processing`.
- Avant cette story, l'API refusait ce statut, ce qui pouvait produire un conflit malgre un controle visible.
- Le runner doit aussi gerer une pause tardive avant publication, car deux callbacks `processing` rapproches peuvent etre filtres par le throttling de progression.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_job_runner.py tests/test_jobs_api.py -q` -> 32 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk uv run ruff check app/api/routes/jobs.py app/services/job_runner.py tests/test_jobs_api.py tests/test_job_runner.py` -> all checks passed
- `rtk uv run pytest -q` -> 64 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk uv run ruff check .` -> all checks passed

### Completion Notes List

- L'API Pause accepte maintenant `queued`, `extracting`, `downloading` et `processing`.
- Le runner appelle une garde explicite apres `downloader.fetch` et avant `publish_file`.
- Ajout d'un test qui simule une pause apres le passage en `processing` et avant publication.

### File List

- `app/api/routes/jobs.py`
- `app/services/job_runner.py`
- `tests/test_jobs_api.py`
- `tests/test_job_runner.py`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/3-3-pause-coherente-pendant-la-phase-de-traitement.md`

## Change Log

- 2026-06-15: Story 3.3 creee, implementee et terminee.
