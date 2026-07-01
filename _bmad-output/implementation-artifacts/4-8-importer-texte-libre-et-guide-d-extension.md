# Story 4.8: Importer texte libre et guide d'extension

Status: done

## Story

En tant qu'utilisateur avance,
je veux importer une liste texte simple et disposer d'un guide pour etendre les sources,
afin d'ajouter des pistes sans dependre d'un format CSV unique.

## Acceptance Criteria

1. Le meme endpoint accepte `importer_key=text` et produit les memes `Track`.
2. Les lignes vides, commentaires et lignes invalides sont gerees explicitement.
3. Aucun changement n'est requis dans le normalizer, la resolution ou la queue.
4. Le guide explique comment enregistrer un importer et un provider.
5. Spotify, Deezer et Apple Music sont documentes comme adaptateurs d'exports fournis
   par l'utilisateur, pas comme contournement d'API ou d'authentification.
6. YouTube Playlist est traite comme importer de metadonnees distinct du provider de
   recherche YouTube.

## Tasks / Subtasks

- [x] Ajouter `PlainTextImporter` avec la cle `text`
- [x] Accepter les fichiers texte sur `POST /api/playlists/import`
- [x] Ignorer lignes vides et commentaires `#`
- [x] Signaler les lignes invalides avec `TEXT_TRACK_FORMAT_INVALID`
- [x] Reutiliser `TrackNormalizer`, la deduplication et le service d'import existants
- [x] Enregistrer l'importer dans `create_app`
- [x] Documenter l'usage texte dans les README
- [x] Documenter le guide d'extension importer/provider
- [x] Ajouter tests unitaires et API
- [x] Executer les controles qualite

## Dev Notes

- Le format texte libre attend une piste par ligne sous la forme `Artist - Title`.
- Les lignes vides et les lignes dont la version trimmee commence par `#` sont ignorees.
- Les lignes invalides, doublons ou sans metadonnees valides deviennent des
  `ImportIssue`; elles ne bloquent pas les pistes valides.
- L'import texte retourne des `ImportedTrack`, puis passe par `PlaylistImportService`;
  aucune adaptation n'a ete necessaire pour le normalizer, la resolution ou la queue.
- La validation d'upload reste specifique aux importers connus, tout en laissant les
  cles inconnues produire l'erreur `PLAYLIST_IMPORTER_UNKNOWN` du registre.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_plain_text_importer.py tests/test_playlists_api.py tests/test_provider_registries.py -q` -> 30 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run pytest -q` -> 130 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run ruff check .` -> all checks passed
- `rtk node --check app/static/app.js` -> syntax OK
- Smoke local `GET /` sur `http://127.0.0.1:8001` -> 200
- Smoke local `POST /api/playlists/import` avec `importer_key=text` -> 201
- `rtk uv run pytest -q` apres polish UI import/segments -> 130 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run ruff check .` apres polish UI import/segments -> all checks passed
- `rtk node --check app/static/app.js` apres polish UI import/segments -> syntax OK

### Completion Notes List

- `importer_key=text` accepte des fichiers `.txt` ou `.text` en `text/plain` ou
  `application/octet-stream`.
- Les README expliquent l'usage du format texte et rappellent que les supports Spotify,
  Deezer et Apple Music doivent rester des adaptateurs d'exports utilisateur.
- Le document d'architecture distingue explicitement importer YouTube Playlist et
  provider de recherche YouTube.
- L'UI expose maintenant l'import de liste depuis la top toolbar dans un dialogue dedie,
  afin de ne pas surcharger le parcours principal URL.
- La decoupe par segments est maintenant activee explicitement via le bouton `Segments`;
  tant que ce panneau n'est pas ouvert, le telechargement reste complet.

### File List

- `README.md`
- `README.fr.md`
- `docs/architecture/playlist_import_architecture.md`
- `app/api/routes/playlists.py`
- `app/main.py`
- `app/services/playlist_import/__init__.py`
- `app/services/playlist_import/plain_text.py`
- `app/static/app.css`
- `app/static/app.js`
- `app/templates/index.html`
- `tests/test_plain_text_importer.py`
- `tests/test_playlists_api.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/4-8-importer-texte-libre-et-guide-d-extension.md`

## Change Log

- 2026-06-26: Story implementee et placee en review.
