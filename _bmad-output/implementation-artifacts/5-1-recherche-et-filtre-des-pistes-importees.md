# Story 5.1: Recherche et filtre des pistes importees

Status: review

## Story

En tant qu'utilisateur,
je veux rechercher et filtrer les pistes d'une playlist importee,
afin de retrouver rapidement les elements a verifier, resoudre ou soumettre.

## Acceptance Criteria

1. Le detail playlist accepte un filtre texte sur artiste, titre, album et ISRC.
2. Le detail playlist accepte un filtre par `resolution_status`.
3. La pagination et le compteur `total_tracks` refletent les filtres actifs.
4. L'interface de revue expose recherche, filtre de statut, application et remise a zero.
5. La selection de pistes est remise a zero quand les filtres changent pour eviter les
   actions en lot sur des pistes masquees.
6. Les tests API couvrent recherche, statut et non-regression du detail pagine.

## Tasks / Subtasks

- [x] Ajouter `q` et `resolution_status` a `GET /api/playlists/{playlist_id}`
- [x] Appliquer les filtres au compteur et a la requete paginee
- [x] Ajouter les controles de recherche/statut dans le dialogue playlist
- [x] Recharger le detail avec `URLSearchParams`
- [x] Reinitialiser la selection lors d'un changement de filtre
- [x] Ajouter un test API de recherche et statut
- [x] Executer les controles qualite

## Dev Notes

- La recherche utilise `ilike` sur `artist`, `title`, `album` et `isrc`.
- Le filtre de statut reutilise l'enum `TrackResolutionStatus`, ce qui garde les valeurs
  API alignees avec le modele.
- Aucun changement n'est apporte a la resolution, a la selection de candidat ni a la
  queue de telechargement.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_playlists_api.py -q` -> 22 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run pytest -q` -> 131 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run ruff check .` -> all checks passed
- `rtk node --check app/static/app.js` -> syntax OK

### Completion Notes List

- Les filtres sont executes cote serveur pour couvrir toute la playlist, pas seulement
  la page courante.
- Le resume de playlist affiche les filtres actifs dans la metadonnee du detail.

### File List

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/5-1-recherche-et-filtre-des-pistes-importees.md`
- `app/api/routes/playlists.py`
- `app/static/app.css`
- `app/static/app.js`
- `app/templates/index.html`
- `tests/test_playlists_api.py`

## Change Log

- 2026-06-27: Story implementee et placee en review.
