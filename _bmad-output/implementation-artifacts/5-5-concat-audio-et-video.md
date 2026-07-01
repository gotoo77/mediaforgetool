# Story 5.5: Concat audio et video

Status: review

## Story

En tant qu'utilisateur,
je veux joindre plusieurs audios ou videos dans un ordre choisi,
afin de produire un fichier final unique sans passer par un outil de montage externe.

## Acceptance Criteria

1. L'Atelier permet de selectionner plusieurs assets audio et de les ordonner.
2. L'Atelier permet de selectionner plusieurs assets video et de les ordonner.
3. `concat_audio` produit un fichier audio unique dans un format compatible choisi.
4. `concat_video` produit un MP4 unique en mode rapide `-c copy` quand les sources sont
   compatibles.
5. Les incompatibilites de codecs, resolution ou conteneur produisent une erreur claire
   et n'ecrasent aucune sortie existante.
6. Les listes temporaires ffmpeg sont creees sous stockage gere, avec chemins echappes
   correctement.
7. Les jobs de concat sont suivis comme les autres jobs d'atelier.

## Tasks / Subtasks

- [x] Ajouter operations `concat_audio` et `concat_video` au constructeur ffmpeg (AC: 3, 4)
- [x] Ajouter generation securisee de fichier concat list (AC: 6)
- [x] Ajouter validations de compatibilite basees sur probe (AC: 5)
- [x] Ajouter UI d'ordre simple haut/bas ou drag minimal (AC: 1, 2)
- [x] Ajouter tests commande, validations et API (AC: 3-7)

## Dev Notes

- V1 peut privilegier la concat rapide et afficher un message explicite si un reencodage
  serait necessaire.
- Le reencodage automatique de videos heterogenes peut etre une story ulterieure.
- Pour audio, viser M4A/AAC ou MP3 selon choix utilisateur.

## Testing Requirements

- Concat audio deux sources.
- Concat video deux sources compatibles.
- Rejet video incompatible.
- Echappement de chemins avec espaces.
- Job echoue sans sortie partielle publiee.

## References

- Story 5.3 runner ffmpeg
- Story 5.4 vue Atelier

## Definition of Done

- Les concat audio/video sont disponibles dans l'Atelier.
- L'ordre des sources est respecte.
- Les erreurs de compatibilite sont claires.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_media_edit.py -q`
- `rtk uv run ruff check .`
- `rtk uv run pytest -q`
- `rtk uv run pytest tests/test_jobs_api.py::test_home_versions_static_assets -q`

### Completion Notes List

- Ajout de `concat_audio` avec fichier concat ffmpeg gere sous `media_studio_dir` et sortie MP3/M4A.
- Ajout de `concat_video` en mode rapide `-c copy` avec rejet des incompatibilites connues.
- Ajout d'un selecteur ordonne dans l'Atelier avec actions ajouter, monter, descendre et retirer.
- Les incompatibilites connues remontent avec `MEDIA_EDIT_INCOMPATIBLE_INPUTS`.

### File List

- `app/core/exceptions.py`
- `app/schemas/studio.py`
- `app/services/media_edit.py`
- `app/templates/index.html`
- `app/static/app.js`
- `app/static/app.css`
- `tests/test_jobs_api.py`
- `tests/test_media_edit.py`

## Change Log

- 2026-06-30: Story creee et placee en ready-for-dev.
- 2026-07-01: Concat audio/video implementee et placee en review.
