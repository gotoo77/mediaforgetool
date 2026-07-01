# Story 4.6: Resolution et ajout en lot controles

Status: done

## Story

En tant qu'utilisateur,
je veux lancer la recherche ou l'ajout a la queue sur une selection de pistes,
afin de traiter plusieurs pistes sans action globale implicite ni contournement de la
queue existante.

## Acceptance Criteria

1. L'utilisateur selectionne les pistes a traiter; aucune action globale implicite.
2. Le nombre de recherches concurrentes est configurable et borne.
3. L'ajout en lot s'arrete proprement lorsque la queue de telechargement est pleine et
   indique les pistes non ajoutees.
4. La progression distingue import, recherche, attente de selection et telechargement.
5. Les operations sont idempotentes et reprenables apres rechargement de page.
6. Une erreur de piste n'annule pas les autres pistes.

## Tasks / Subtasks

- [x] Ajouter `MEDIA_RESOLUTION_MAX_CONCURRENCY`
- [x] Exposer la resolution batch sur une selection de pistes
- [x] Borner la concurrence effective au parametre d'instance
- [x] Exposer l'ajout batch a la queue sur une selection de candidats
- [x] Arreter l'ajout batch sur `QUEUE_FULL` et reporter les pistes ignorees
- [x] Renvoyer une progression par piste avec phase et statut
- [x] Ajouter selection explicite des pistes dans l'UI
- [x] Ajouter actions UI "Rechercher selection" et "Ajouter selection"
- [x] Ajouter tests batch resolution, batch queue et garde-fous de routes
- [x] Executer les controles qualite

## Dev Notes

- La resolution batch utilise des sessions SQLAlchemy separees par worker et un
  `ThreadPoolExecutor` borne par `MEDIA_RESOLUTION_MAX_CONCURRENCY`.
- L'ajout batch reste sequentiel pour respecter l'arret immediat sur queue pleine.
- Les resultats de batch indiquent `search`, `selection` ou `download` pour distinguer
  les phases et permettre a l'UI de resume l'etat.
- La reprise apres rechargement s'appuie sur les candidats, statuts de piste et queue
  items persistants deja exposes par le detail playlist.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_playlists_api.py tests/test_media_resolution.py tests/test_playlist_queue.py -q`
  -> 24 passed
- `rtk uv run pytest -q` -> 122 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run ruff check .` -> all checks passed
- `rtk node --check app/static/app.js` -> syntax OK

### Completion Notes List

- Les batchs exigent une selection explicite de pistes.
- La resolution batch ne bloque pas tout le lot quand une piste echoue ou ne retourne
  aucun resultat.
- L'ajout batch s'arrete sur queue pleine et marque les pistes restantes comme ignorees.
- L'UI conserve les actions unitaires et ajoute une barre de batch pour la page courante.

### File List

- `.env.example`
- `app/api/dependencies.py`
- `app/api/routes/playlists.py`
- `app/core/config.py`
- `app/schemas/playlist.py`
- `app/static/app.css`
- `app/static/app.js`
- `app/templates/index.html`
- `tests/test_playlist_domain.py`
- `tests/test_playlists_api.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/4-6-resolution-et-ajout-en-lot-controles.md`

## Change Log

- 2026-06-26: Story implementee et placee en review.
