# Story 5.3: Jobs ffmpeg V1 de transformation simple

Status: review

## Story

En tant qu'utilisateur,
je veux remplacer l'audio d'une video, retirer l'audio, extraire l'audio et decouper un
media en deux,
afin de realiser les corrections media les plus courantes depuis le navigateur.

## Acceptance Criteria

1. Un runner d'atelier execute les jobs `replace_audio`, `remove_audio`, `extract_audio`
   et `split_media` avec `ffmpeg`.
2. Les commandes sont construites via listes d'arguments, jamais via shell string.
3. `replace_audio` supporte un decalage audio en secondes, un mode `shortest` et une
   sortie MP4 compatible.
4. `remove_audio` copie la piste video sans audio quand le conteneur le permet.
5. `extract_audio` produit MP3 ou M4A selon option explicite.
6. `split_media` produit deux assets de sortie a partir d'un timecode unique.
7. Le runner met a jour statut, progression minimale, chemin de sortie et erreurs.
8. Les operations refusent les inputs incompatibles avant lancement quand l'inspection
   disponible le permet.
9. Les tests couvrent la construction de commandes et les transitions de statuts sans
   lancer de media lourd.

## Tasks / Subtasks

- [x] Definir schemas de creation de jobs d'atelier V1 (AC: 1, 3-6)
- [x] Implementer constructeur de commandes ffmpeg testable (AC: 2)
- [x] Implementer runner synchrone coherent avec `JobRunner` existant (AC: 7)
- [x] Persister assets de sortie pour chaque operation (AC: 6, 7)
- [x] Ajouter validations d'inputs basees sur kind/probe path disponible (AC: 8)
- [x] Ajouter endpoints creation/statut/fichier pour jobs atelier (AC: 1, 7)
- [x] Ajouter tests commande et API (AC: 9)

## Dev Notes

Commandes cibles initiales:

- Remplacer audio:
  `ffmpeg -i video.mp4 -itsoffset <offset> -i audio -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest output.mp4`
- Retirer audio:
  `ffmpeg -i video.mp4 -map 0:v:0 -c:v copy -an output.mp4`
- Extraire audio:
  `ffmpeg -i video.mp4 -vn -c:a libmp3lame output.mp3`
- Decouper:
  `ffmpeg -i source -t <cut> -c copy part1`
  `ffmpeg -ss <cut> -i source -c copy part2`

Le mode precis/reencodage complet peut rester hors V1 si le mode rapide est documente.

## Testing Requirements

- Tests unitaires de commande pour chaque operation.
- Tests de validation input audio/video.
- Tests de job reussi avec subprocess fake.
- Tests de job echoue avec stderr capture.
- Tests API creation/statut/fichier.

## References

- `app/services/job_runner.py`
- `app/services/media_downloader.py`
- `app/services/storage_service.py`
- `tests/test_job_runner.py`

## Definition of Done

- Les quatre operations V1 sont disponibles via API.
- Les outputs sont tracables comme assets.
- Les erreurs ffmpeg sont visibles et stables.
- Les tests cibles passent.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_media_edit.py -q` -> 5 passed
- `rtk uv run pytest tests/test_studio_domain.py tests/test_media_probe.py tests/test_media_edit.py -q` -> 20 passed
- `rtk uv run ruff check .` -> all checks passed
- `rtk uv run pytest -q` -> 102 passed

### Completion Notes List

- Ajout des schemas de creation et reponse de jobs d'atelier.
- Ajout de `MediaEditCommandBuilder` pour construire les commandes ffmpeg en listes
  d'arguments.
- Ajout de `MediaEditRunner` synchrone V1 pour executer les operations et publier les
  sorties comme `MediaAsset`.
- Operations V1 disponibles: remplacer audio, retirer audio, extraire audio, decouper en
  deux.
- Ajout des endpoints `POST /api/studio/jobs`, `GET /api/studio/jobs/{id}` et
  `GET /api/studio/jobs/{id}/file`.
- Les erreurs d'input invalide produisent un job `failed` avec code stable.

### File List

- `app/api/routes/studio.py`
- `app/core/exceptions.py`
- `app/db/init_db.py`
- `app/models/__init__.py`
- `app/models/studio.py`
- `app/schemas/studio.py`
- `app/services/media_edit.py`
- `tests/test_media_edit.py`
- `tests/test_studio_domain.py`
- `_bmad-output/implementation-artifacts/5-1-socle-domaine-atelier-et-assets-media.md`
- `_bmad-output/implementation-artifacts/5-3-jobs-ffmpeg-v1-de-transformation-simple.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-06-30: Story creee et placee en ready-for-dev.
- 2026-06-30: Jobs ffmpeg V1 implementes et story placee en review.
