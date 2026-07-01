# Story 5.2: Inspection locale audio/video

Status: review

## Story

En tant qu'utilisateur,
je veux que l'atelier inspecte les fichiers audio/video disponibles,
afin de voir duree, codecs, pistes, resolution et compatibilite avant de lancer une
operation.

## Acceptance Criteria

1. Un service `MediaProbeService` appelle `ffprobe` via arguments structures et timeout.
2. Le resultat d'inspection expose duree, conteneur, taille, pistes audio/video, codec,
   bitrate, resolution et presence audio/video.
3. Les erreurs `ffprobe` sont transformees en erreurs applicatives stables et
   comprehensibles.
4. Le service refuse d'inspecter des chemins hors des repertoires geres par l'application.
5. Un endpoint interne/public d'atelier permet d'inspecter un asset existant.
6. Les tests mockent `subprocess` et ne dependent pas de vrais fichiers media lourds.
7. Les donnees d'inspection peuvent etre stockees sur `MediaAsset` ou retournees sans
   casser le schema de la story 5.1.

## Tasks / Subtasks

- [x] Definir les schemas de probe audio/video (AC: 2)
- [x] Implementer `MediaProbeService` autour de `ffprobe -print_format json` (AC: 1)
- [x] Ajouter validation de chemin sous stockage gere (AC: 4)
- [x] Ajouter erreurs applicatives `MediaProbeFailed`, `MediaAssetUnavailable` (AC: 3)
- [x] Ajouter endpoint d'inspection asset (AC: 5)
- [x] Ajouter tests unitaires service avec sorties `ffprobe` fake (AC: 6)
- [x] Ajouter tests API d'inspection (AC: 5)

## Dev Notes

- Utiliser `subprocess.run([...], shell=False, capture_output=True, text=True, timeout=...)`.
- Ne pas parser stdout par regex; charger le JSON produit par `ffprobe`.
- Les fichiers sans audio ou sans video sont valides: le type determine les operations
  autorisees ensuite.
- Prevoir une duree `None` si le conteneur ne fournit pas l'information.

## Testing Requirements

- Inspection video avec audio.
- Inspection audio seul.
- Inspection video muette.
- Fichier absent.
- Sortie ffprobe invalide.
- Timeout ffprobe.
- Rejet chemin hors stockage.

## References

- `app/core/config.py`
- `app/main.py` pour validation binaire `ffprobe`
- `app/api/routes/jobs.py` pour conventions d'erreurs API

## Definition of Done

- Les assets peuvent etre probes via service et API.
- Les erreurs sont stables et testees.
- Aucun appel reseau n'est introduit.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest tests/test_media_probe.py -q` -> 5 passed
- `uv run pytest tests/test_studio_domain.py -q` -> 9 passed
- `uv run pytest tests/test_media_probe.py tests/test_studio_domain.py -q` -> 14 passed
- `uv run pytest -q` -> 96 passed
- `uv run ruff check .` -> all checks passed

### Completion Notes List

- Ajout des schemas de probe audio/video et inspection d'asset.
- Ajout de `MediaProbeService` base sur `ffprobe` JSON avec timeout et shell=False.
- Ajout de la validation des chemins relatifs sous stockage gere.
- Ajout des erreurs applicatives `MediaAssetUnavailable` et `MediaProbeFailed`.
- Ajout de la route `GET /api/studio/assets/{asset_id}/inspect`.
- Preparation des dossiers `media_assets_dir` et `media_studio_dir` au demarrage.

### File List

- `app/api/routes/studio.py`
- `app/core/exceptions.py`
- `app/main.py`
- `app/schemas/studio.py`
- `app/services/media_probe.py`
- `app/services/storage_service.py`
- `tests/test_media_probe.py`
- `_bmad-output/implementation-artifacts/5-2-inspection-locale-audio-video.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-06-30: Story creee et placee en ready-for-dev.
- 2026-06-30: Inspection locale implemente et story placee en review.
