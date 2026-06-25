# Story 1.1: Socle FastAPI, jobs et telechargement media MVP

Status: done

## Story

En tant qu'utilisateur self-hosted,
je veux soumettre une URL publique, choisir MP4 ou MP3, suivre le traitement et recuperer le fichier final,
afin de telecharger un media sans compte utilisateur.

## Acceptance Criteria

1. L'application expose une interface web FastAPI/Jinja avec un champ URL, un choix MP4/MP3, des presets de resolution MP4 et un historique local minimal.
2. L'API permet d'inspecter une source, de creer un job, de lire son statut, de lister les jobs recents et de telecharger le fichier final quand le job est termine.
3. Les jobs sont persistants en SQLite avec statut, progression, metadonnees source, chemin de sortie, taille, erreurs et dates utiles.
4. Le runner traite les jobs en arriere-plan avec une file bornee, une concurrence configurable, une recuperation des jobs queued au demarrage et une interruption explicite des jobs actifs apres redemarrage.
5. L'integration `yt-dlp`/`ffmpeg` produit des sorties MP4 ou MP3 dans `storage/jobs`, respecte les limites de duree/taille/configuration et publie seulement l'artefact final.
6. Les URLs acceptees sont limitees aux URLs HTTP(S) publiques avec garde SSRF de base contre destinations privees, loopback et link-locales.
7. Le service applique un rate limit local par client, nettoie les fichiers temporaires et expire les sorties retenues.
8. La configuration, Docker, README et tests permettent de lancer et verifier le MVP localement.

## Tasks / Subtasks

- [x] Verifier le socle applicatif FastAPI (AC: 1, 2, 8)
  - [x] Confirmer la factory d'application, le routage page/API et le montage des assets statiques.
  - [x] Confirmer le template Jinja et les assets navigateur pour formulaire, inspection, progression et historique.
  - [x] Confirmer la documentation de lancement local et Docker.
- [x] Verifier la persistence et les schemas de jobs (AC: 2, 3)
  - [x] Confirmer le modele `DownloadJob` et ses statuts.
  - [x] Confirmer les schemas de creation, inspection et reponse.
  - [x] Confirmer les endpoints `POST /api/jobs/inspect`, `POST /api/jobs`, `GET /api/jobs`, `GET /api/jobs/{job_id}`, `GET /api/jobs/{job_id}/file`.
- [x] Verifier le runner et les services media (AC: 4, 5, 7)
  - [x] Confirmer la file bornee, les workers, le throttling de progression et la gestion timeout/echec.
  - [x] Confirmer la publication finale dans `storage/jobs` et le nettoyage de `temp/jobs`.
  - [x] Confirmer l'expiration des sorties et la retention configurable.
- [x] Verifier les protections MVP (AC: 6, 7)
  - [x] Confirmer la validation d'URL publique.
  - [x] Confirmer le rate limit de creation/inspection de jobs.
  - [x] Confirmer que les cookies restent une configuration instance-level, sans upload utilisateur.
- [x] Executer les controles de qualite (AC: 8)
  - [x] Executer `rtk uv run ruff check .`.
  - [x] Executer `rtk uv run pytest`.

## Dev Notes

### Etat actuel a preserver

- `app/main.py` construit l'application, initialise la base, demarre le runner et le cleanup service via lifespan.
- `app/api/routes/jobs.py` porte les endpoints job/inspection/fichier sans realiser le travail bloquant dans la route.
- `app/services/job_runner.py` garde la frontiere queue/worker et execute `yt-dlp` via `asyncio.to_thread`.
- `app/services/media_downloader.py` isole l'integration `yt-dlp` et les choix de format.
- `app/services/storage_service.py` publie le fichier final et retire les fichiers temporaires.
- `app/services/url_guard.py` fournit la garde SSRF de base.
- Le README declare le perimetre Phase 1 et les exclusions: comptes, OAuth, playlists, batch jobs, queue distribuee et cookies utilisateur.

### Architecture et contraintes

- Stack declaree: Python 3.12+, FastAPI, SQLAlchemy, SQLite, Jinja2, Uvicorn, `yt-dlp`, `ffmpeg`.
- Le MVP est mono-processus. Plusieurs workers Uvicorn creeraient plusieurs queues memoire et sortent du modele Phase 1.
- `yt-dlp` et `ffmpeg` possedent le comportement extraction/conversion; MediaForgeTool orchestre, limite et expose le workflow.
- Les tests doivent mocker la frontiere plateforme au lieu de telecharger des medias publics.

### Fichiers probablement touches

- `README.md`
- `docs/architecture.md`
- `app/main.py`
- `app/api/routes/jobs.py`
- `app/models/job.py`
- `app/schemas/job.py`
- `app/services/job_runner.py`
- `app/services/media_downloader.py`
- `app/services/storage_service.py`
- `app/services/cleanup_service.py`
- `app/services/url_guard.py`
- `app/static/app.js`
- `app/static/app.css`
- `app/templates/index.html`
- `tests/test_jobs_api.py`
- `tests/test_job_runner.py`
- `tests/test_media_downloader.py`
- `tests/test_url_guard.py`

### Tests attendus

- `rtk uv run pytest`
- `rtk uv run ruff check .`

### References

- `README.md`: perimetre Phase 1, lancement, API, configuration, securite et tests.
- `docs/architecture.md`: contraintes et flux de traitement.
- `_bmad-output/planning-artifacts/epics.md`: Epic 1 et Story 1.1.

## Out of Scope

- Comptes utilisateurs, OAuth et authentification applicative.
- Playlists, batch jobs et queue distribuee.
- Upload de cookies par l'utilisateur.
- Multi-process Uvicorn ou orchestration distribuee.
- Validation exhaustive reseau de niveau sandbox pour exposition Internet publique.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run ruff check .` -> all checks passed
- `rtk uv run pytest` -> 21 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk uv run ruff check .` -> all checks passed
- `rtk uv run pytest` -> 21 passed, 1 pytest-asyncio deprecation warning under Python 3.14

### Completion Notes List

- Story artifact created after implementation from the existing README, architecture record and codebase.
- MVP implementation is present: web UI, API routes, SQLite persistence, background runner, downloader integration, storage/cleanup, URL guard and rate limiting.
- Verification passed with lint and tests.
- Remaining review risk is operational/manual: real-platform extractor behavior depends on current `yt-dlp`, `ffmpeg`, optional JavaScript runtime and platform-specific access constraints.
- Code review completed without blocking findings for the Story 1.1 acceptance criteria.

### File List

- `_bmad-output/implementation-artifacts/1-1-socle-fastapi-jobs-et-telechargement-media-mvp.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `README.md`
- `docs/architecture.md`
- `app/main.py`
- `app/api/routes/jobs.py`
- `app/models/job.py`
- `app/schemas/job.py`
- `app/services/job_runner.py`
- `app/services/media_downloader.py`
- `app/services/storage_service.py`
- `app/services/cleanup_service.py`
- `app/services/url_guard.py`
- `app/static/app.js`
- `app/static/app.css`
- `app/templates/index.html`
- `tests/test_jobs_api.py`
- `tests/test_job_runner.py`
- `tests/test_media_downloader.py`
- `tests/test_url_guard.py`

## Change Log

- 2026-05-31: Story 1.1 creee depuis l'implementation existante et mise en review avec verification lint/tests.
- 2026-05-31: Code review Story 1.1 approuvee sans finding bloquant; story terminee.

## QA Results

### Review Date

2026-05-31

### Reviewed By

GPT-5 Codex

### Findings

Aucun finding bloquant.

### Acceptance Criteria Coverage

- AC1-AC2: Interface web, routes pages/API et endpoints jobs verifies dans `app/main.py`, `app/api/routes/jobs.py`, `app/templates/index.html`, `app/static/app.js`.
- AC3: Persistence job et champs de suivi verifies dans `app/models/job.py` et `app/schemas/job.py`.
- AC4: Runner, file bornee, reprise queued et interruption jobs actifs verifies dans `app/services/job_runner.py` et tests associes.
- AC5: Integration `yt-dlp`/`ffmpeg`, limites duree/taille, formats MP3/MP4 et publication finale verifies dans `app/services/media_downloader.py` et `app/services/storage_service.py`.
- AC6: Garde URL publique HTTP(S) et rejets loopback/credentials verifies dans `app/services/url_guard.py` et tests associes.
- AC7: Rate limiting, nettoyage temporaire et expiration sorties verifies dans `app/api/routes/jobs.py`, `app/services/rate_limiter.py`, `app/services/cleanup_service.py`.
- AC8: Documentation et verification locale confirmees.

### Verification

- `rtk uv run ruff check .` -> passed
- `rtk uv run pytest` -> 21 passed, 1 warning pytest-asyncio sous Python 3.14

### Residual Risk

- Le comportement reel des plateformes depend de `yt-dlp`, de `ffmpeg`, du runtime JavaScript optionnel et des exigences cookies/acces propres aux sources.
- La garde SSRF est une protection applicative de base; elle ne remplace pas une sandbox reseau pour une exposition publique Internet.
