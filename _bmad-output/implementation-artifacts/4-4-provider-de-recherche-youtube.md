# Story 4.4: Provider de recherche YouTube

Status: done

## Story

En tant qu'utilisateur,
je veux rechercher des candidats YouTube pour une piste importee,
afin de choisir ulterieurement le media a ajouter a la queue de telechargement.

## Acceptance Criteria

1. Le provider construit une requete deterministe a partir de l'artiste et du titre.
2. Il retourne des `ResolvedMediaCandidate` avec URL, titre, chaine/artiste, duree,
   miniature, provider et score/rang.
3. La recherche utilise `yt-dlp` en mode extraction sans telechargement ou un adaptateur
   equivalent, sans reintroduire cette logique dans la route HTTP.
4. Les resultats sont limites et persistes par piste.
5. Les erreurs d'authentification, absence de resultat, timeout et indisponibilite sont
   mappees vers des codes publics propres.
6. Une nouvelle recherche remplace proprement les anciens candidats du provider.
7. Aucune recherche ne cree de `DownloadJob`.

## Tasks / Subtasks

- [x] Ajouter la limite configurable de candidats de recherche
- [x] Implementer le provider `youtube` avec frontiere `yt-dlp` injectable
- [x] Mapper les resultats `yt-dlp` vers `SearchCandidate`
- [x] Mapper les erreurs provider vers des codes publics stables
- [x] Ajouter un service de resolution piste -> provider -> candidats persistants
- [x] Remplacer les anciens candidats du meme provider lors d'une nouvelle recherche
- [x] Exposer `POST /api/playlists/{playlist_id}/tracks/{track_id}/resolve`
- [x] Afficher les candidats et l'action de recherche dans la revue de playlist
- [x] Ajouter tests provider, service et API
- [x] Executer les controles qualite

## Dev Notes

- Le provider utilise `ytsearchN:<artiste> <titre>` avec `download=False` et
  `skip_download=True`.
- Les tests mockent strictement la fabrique `YoutubeDL`; aucun reseau n'est requis.
- L'endpoint reste sous `/api/playlists` pour eviter d'introduire une surface
  `/api/tracks` separee.
- L'ajout a la queue et la selection explicite d'un candidat restent hors scope et
  appartiennent a la Story 4.5.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_youtube_search_provider.py tests/test_media_resolution.py tests/test_playlists_api.py -q`
  -> 22 passed
- `rtk node --check app/static/app.js` -> syntax OK
- `rtk uv run pytest -q` -> 110 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run ruff check .` -> all checks passed

### Completion Notes List

- Le provider YouTube est enregistre au demarrage de l'application.
- Les recherches mettent la piste en `resolved`, `no_match` ou `failed`.
- Les candidats sont persistants et visibles dans le detail de playlist.
- Aucun `DownloadJob` n'est cree pendant la resolution.

### File List

- `.env.example`
- `app/api/dependencies.py`
- `app/api/routes/playlists.py`
- `app/core/config.py`
- `app/core/exceptions.py`
- `app/main.py`
- `app/schemas/playlist.py`
- `app/services/media_resolution.py`
- `app/services/media_search/__init__.py`
- `app/services/media_search/youtube.py`
- `app/static/app.css`
- `app/static/app.js`
- `tests/test_media_resolution.py`
- `tests/test_playlist_domain.py`
- `tests/test_playlists_api.py`
- `tests/test_youtube_search_provider.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/4-4-provider-de-recherche-youtube.md`

## Change Log

- 2026-06-26: Story implementee et placee en review.
