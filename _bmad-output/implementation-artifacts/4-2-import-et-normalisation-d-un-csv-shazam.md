# Story 4.2: Import et normalisation d'un CSV Shazam

Status: done

## Story

En tant qu'utilisateur,
je veux importer un export CSV Shazam et obtenir des pistes normalisees,
afin de verifier ma liste avant toute recherche ou tout telechargement.

## Acceptance Criteria

1. Un fichier CSV Shazam UTF-8 valide produit une `ImportedPlaylist` et des `Track`.
2. Le parseur accepte les variantes documentees de noms de colonnes Shazam.
3. Les espaces, valeurs vides, marqueurs explicites de version et doublons exacts sont
   traites de maniere deterministe.
4. Chaque piste conserve la ligne source et les valeurs brutes utiles au diagnostic.
5. Les lignes invalides n'annulent pas tout l'import; elles sont comptees et exposees
   avec un message actionnable.
6. La taille du fichier, le nombre de lignes et le type de fichier sont limites.
7. Aucun `DownloadJob` n'est cree pendant l'import.
8. Les logs indiquent le debut, la fin partielle ou complete et les erreurs d'import sans
   contenir le fichier complet.
9. Le README anglais et francais documente l'import CSV et son absence de telechargement
   implicite.
10. Les tests cibles et complets ainsi que Ruff passent.

## Tasks / Subtasks

- [x] Ajouter les limites de taille et de lignes dans la configuration
- [x] Ajouter un normaliseur conservatif et versionne
- [x] Implementer l'importer `shazam_csv` via le registre existant
- [x] Gerer UTF-8 BOM, virgule, point-virgule et tabulation
- [x] Reconnaitre les variantes de colonnes titre, artiste, album, ISRC et duree
- [x] Detecter les lignes incompletes et doublons exacts
- [x] Borner le payload source conserve par piste
- [x] Persister playlist, pistes, compteurs et resume d'erreurs
- [x] Exposer `POST /api/playlists/import` en multipart
- [x] Refuser les fichiers trop grands, formats non supportes et listes trop longues
- [x] Ajouter les logs d'import
- [x] Documenter le parcours en anglais et en francais
- [x] Ajouter fixtures et tests unitaires/API
- [x] Executer les controles qualite

## Dev Notes

- La normalisation applique Unicode NFKC, reduit les espaces et conserve les marqueurs
  musicaux explicites comme `Live`, `Remix` ou `Remastered`.
- Les doublons sont compares sur artiste, titre, album et ISRC normalises.
- Les lignes invalides et doublons sont retournes dans `issues`; un resume agrege est
  persiste dans `ImportedPlaylist.error_summary`.
- Le fichier complet n'est jamais persiste.
- Le endpoint accepte uniquement un fichier `.csv` avec un type MIME CSV, texte ou
  binaire generique.
- L'import utilise le registre `PlaylistImporterRegistry`; aucune conditionnelle Shazam
  n'est ajoutee dans la route.
- Aucun provider, `MediaDownloader`, `JobRunner` ou `DownloadJob` n'est appele.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_shazam_csv_importer.py tests/test_playlists_api.py -q`
  -> 10 passed
- `rtk uv run pytest tests/test_shazam_csv_importer.py tests/test_playlists_api.py
  tests/test_logging.py -q` -> 15 passed
- `rtk uv run pytest -q` -> 94 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run --isolated --python 3.12 pytest tests/test_shazam_csv_importer.py
  tests/test_playlists_api.py tests/test_logging.py tests/test_playlist_domain.py -q`
  -> 24 passed
- `rtk uv run ruff check .` -> all checks passed
- `rtk docker build -t mediaforgetool:story-4-2-check .` -> image built successfully
- Smoke test Docker `POST /api/playlists/import` avec `basic.csv` -> playlist `ready`,
  2 pistes, 0 issue

### Completion Notes List

- Import CSV Shazam persiste avec statut `ready` ou `partial`.
- Les erreurs ligne par ligne n'annulent pas les pistes valides.
- Les limites `PLAYLIST_IMPORT_MAX_BYTES` et `PLAYLIST_IMPORT_MAX_TRACKS` sont
  configurables.
- La reponse API contient playlist, pistes et issues.
- Aucun job de telechargement n'est cree.

### File List

- `.env.example`
- `README.md`
- `README.fr.md`
- `pyproject.toml`
- `requirements/base.txt`
- `uv.lock`
- `app/api/dependencies.py`
- `app/api/routes/playlists.py`
- `app/core/config.py`
- `app/core/exceptions.py`
- `app/core/logging.py`
- `app/main.py`
- `app/schemas/playlist.py`
- `app/services/track_normalizer.py`
- `app/services/playlist_import/__init__.py`
- `app/services/playlist_import/service.py`
- `app/services/playlist_import/shazam_csv.py`
- `tests/fixtures/shazam/basic.csv`
- `tests/fixtures/shazam/partial_semicolon.csv`
- `tests/test_logging.py`
- `tests/test_playlists_api.py`
- `tests/test_shazam_csv_importer.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/4-2-import-et-normalisation-d-un-csv-shazam.md`

## Change Log

- 2026-06-25: Story implementee et placee en review.
