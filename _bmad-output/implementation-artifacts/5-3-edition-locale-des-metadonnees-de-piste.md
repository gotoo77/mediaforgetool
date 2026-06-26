# Story 5.3: Edition locale des metadonnees de piste

Status: review

## Story

En tant qu'utilisateur,
je veux corriger localement artiste, titre, album et ISRC d'une piste importee,
afin d'ameliorer la recherche de candidats sans modifier le fichier source.

## Acceptance Criteria

1. Une route permet de mettre a jour artiste, titre, album et ISRC d'une piste d'une
   playlist.
2. Artiste et titre restent obligatoires et sont normalises comme a l'import.
3. La piste modifiee reste dans la meme playlist et conserve sa position.
4. Une piste non liee a un queue item repasse en statut `pending` apres correction.
5. L'interface expose une action `Modifier` par piste avec formulaire inline.
6. La recherche et le detail reflètent les metadonnees corrigees.
7. Les tests API couvrent edition, normalisation, recherche post-edition et piste absente.

## Tasks / Subtasks

- [x] Ajouter `UpdateTrackRequest`
- [x] Ajouter `PATCH /api/playlists/{playlist_id}/tracks/{track_id}`
- [x] Renormaliser artiste, titre, album et ISRC via `TrackNormalizer`
- [x] Remettre le statut a `pending` quand la piste n'a pas de queue item
- [x] Ajouter l'action UI `Modifier` et un formulaire inline compact
- [x] Recharger le detail apres sauvegarde
- [x] Ajouter tests API
- [x] Executer les controles qualite

## Dev Notes

- Les candidats deja persistants ne sont pas supprimes dans cette story afin de ne pas
  casser les references de queue items. Une future story pourra ajouter un statut
  d'obsolescence des candidats.
- Les valeurs brutes `raw_artist` et `raw_title` sont mises a jour avec la saisie
  utilisateur.
- Le fichier source importe n'est pas modifie.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_playlists_api.py -q` -> 25 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run pytest -q` -> 134 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run ruff check .` -> all checks passed
- `rtk node --check app/static/app.js` -> syntax OK

### Completion Notes List

- Le formulaire inline est cree a la demande et peut etre annule sans appel API.
- La sauvegarde recharge la page courante de playlist pour garder filtres, tri et
  selection coherents.

### File List

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/5-3-edition-locale-des-metadonnees-de-piste.md`
- `app/api/routes/playlists.py`
- `app/schemas/playlist.py`
- `app/static/app.css`
- `app/static/app.js`
- `tests/test_playlists_api.py`

## Change Log

- 2026-06-27: Story implementee et placee en review.
