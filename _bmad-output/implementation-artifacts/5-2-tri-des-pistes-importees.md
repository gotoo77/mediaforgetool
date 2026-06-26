# Story 5.2: Tri des pistes importees

Status: review

## Story

En tant qu'utilisateur,
je veux trier les pistes d'une playlist importee,
afin de comparer plus facilement les artistes, titres, albums et statuts de resolution.

## Acceptance Criteria

1. Le detail playlist accepte un champ de tri stable.
2. Le detail playlist accepte un sens ascendant ou descendant.
3. Les tris disponibles couvrent ordre d'import, artiste, titre, album et statut de
   resolution.
4. La pagination reste appliquee apres filtre et tri.
5. L'interface expose le champ de tri et le sens dans la barre de revue.
6. Les tests API couvrent au moins deux tris avec ordre attendu.

## Tasks / Subtasks

- [x] Ajouter `sort` et `direction` a `GET /api/playlists/{playlist_id}`
- [x] Appliquer un ordre SQL stable avec `position` comme tie-breaker hors tri position
- [x] Ajouter les controles de tri dans le formulaire de revue playlist
- [x] Envoyer `sort` et `direction` avec les filtres existants
- [x] Afficher le tri actif dans le resume de detail quand il n'est pas par defaut
- [x] Ajouter un test API de tri
- [x] Executer les controles qualite

## Dev Notes

- Les valeurs de tri sont bornees par `Literal` cote route FastAPI.
- Le tri par defaut reste `position asc`, ce qui preserve l'ordre d'import historique.
- Aucun changement n'est apporte aux candidats, aux jobs ou a la queue.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_playlists_api.py -q` -> 23 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run pytest -q` -> 132 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run ruff check .` -> all checks passed
- `rtk node --check app/static/app.js` -> syntax OK

### Completion Notes List

- Les tris disponibles sont `position`, `artist`, `title`, `album` et
  `resolution_status`.
- Le sens disponible est `asc` ou `desc`.

### File List

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/5-2-tri-des-pistes-importees.md`
- `app/api/routes/playlists.py`
- `app/static/app.js`
- `app/templates/index.html`
- `tests/test_playlists_api.py`

## Change Log

- 2026-06-27: Story implementee et placee en review.
