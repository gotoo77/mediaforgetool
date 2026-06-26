# Story 4.5: Selection d'un candidat et ajout a la queue existante

Status: done

## Story

En tant qu'utilisateur,
je veux choisir explicitement un candidat resolu et l'ajouter a la queue existante,
afin de lancer le telechargement via le parcours deja controle.

## Acceptance Criteria

1. Un candidat doit etre selectionne explicitement avant l'ajout a la queue.
2. Le service d'orchestration reutilise la meme validation et la meme creation de job
   que `POST /api/jobs`, sans dupliquer les regles metier.
3. `DownloadQueueItem` reference le `Track`, le candidat et le `DownloadJob` cree.
4. Les limites de queue et erreurs `QUEUE_FULL` restent identiques au parcours URL.
5. La piste affiche le statut du job associe et un lien vers l'historique existant.
6. Un double clic ou une requete repetee ne cree pas deux jobs par inadvertance.
7. Pause, reprise, suppression, retention et telechargement final continuent d'utiliser
   les endpoints de jobs existants.

## Tasks / Subtasks

- [x] Extraire la creation de job dans `JobSubmissionService`
- [x] Faire reutiliser ce service par `POST /api/jobs`
- [x] Ajouter `PlaylistQueueService` pour candidat -> queue item -> job
- [x] Ajouter l'idempotence piste/candidat/format/options
- [x] Exposer l'endpoint de queue candidat sous `/api/playlists`
- [x] Afficher les controles format/options et l'etat queue dans l'UI playlist
- [x] Conserver les candidats deja soumis lors d'une nouvelle recherche
- [x] Ajouter tests service, API et non-regression jobs
- [x] Executer les controles qualite

## Dev Notes

- Le nouvel endpoint est
  `POST /api/playlists/{playlist_id}/tracks/{track_id}/candidates/{candidate_id}/queue`.
- L'idempotency key combine piste, candidat, format, resolution et bitrate.
- `QUEUE_FULL` reste mappe en HTTP 503 avec le meme code public que le parcours URL.
- Les jobs crees par playlist restent des `DownloadJob` ordinaires: historique, pause,
  reprise, suppression, retention et fichier final restent geres par `/api/jobs`.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_job_submission.py tests/test_playlist_queue.py tests/test_playlists_api.py tests/test_jobs_api.py -q`
  -> 47 passed
- `rtk uv run pytest -q` -> 120 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run ruff check .` -> all checks passed
- `rtk node --check app/static/app.js` -> syntax OK

### Completion Notes List

- Le parcours URL et le parcours playlist partagent `JobSubmissionService`.
- Un candidat ajoute cree un `DownloadQueueItem` et un `DownloadJob` enfile.
- Les requetes repetees avec les memes options retournent le meme queue item.
- L'UI permet de choisir MP3/MP4 et leurs options avant ajout.

### File List

- `app/api/routes/jobs.py`
- `app/api/routes/playlists.py`
- `app/core/exceptions.py`
- `app/schemas/playlist.py`
- `app/services/job_submission.py`
- `app/services/media_resolution.py`
- `app/services/playlist_queue.py`
- `app/static/app.css`
- `app/static/app.js`
- `tests/test_job_submission.py`
- `tests/test_media_resolution.py`
- `tests/test_playlist_domain.py`
- `tests/test_playlist_queue.py`
- `tests/test_playlists_api.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/4-5-selection-d-un-candidat-et-ajout-a-la-queue-existante.md`

## Change Log

- 2026-06-26: Story implementee et placee en review.
