# Story 5.1: Socle domaine Atelier et assets media

Status: review

## Story

En tant que mainteneur,
je veux disposer d'un domaine `MediaAsset` et `MediaEditJob` separe du pipeline de
telechargement,
afin de tracer les fichiers locaux, les operations ffmpeg et les sorties d'atelier sans
coupler ces traitements aux `DownloadJob`.

## Acceptance Criteria

1. Un modele `MediaAsset` persiste les fichiers connus de l'atelier avec identifiant
   stable, nom, chemin relatif, type media, mime/type de conteneur, taille, origine et
   dates.
2. Un modele `MediaEditJob` persiste les operations d'atelier, leurs entrees, options,
   sortie attendue, statut, progression, erreurs et dates.
3. Les statuts d'edition sont distincts de `JobStatus` et couvrent au minimum `queued`,
   `probing`, `processing`, `completed`, `failed`, `cancelled`.
4. Les operations supportees sont enumerees sans string libre: `replace_audio`,
   `remove_audio`, `extract_audio`, `split_media`, `concat_audio`, `concat_video`.
5. Le schema SQLite se cree sur base vide et s'ajoute a une base existante sans modifier
   les tables de jobs de telechargement.
6. Les chemins stockes restent sous les repertoires geres par l'application.
7. Aucun endpoint public ni changement UI n'est requis dans cette story.
8. Les tests de domaine et schema couvrent creation, relations, transitions et upgrade
   additif.

## Tasks / Subtasks

- [x] Definir les enums `MediaAssetKind`, `MediaAssetOrigin`, `MediaEditOperation`,
  `MediaEditStatus` (AC: 1, 3, 4)
- [x] Ajouter le modele ORM `MediaAsset` (AC: 1, 6)
- [x] Ajouter le modele ORM `MediaEditJob` avec relation vers assets d'entree et asset
  de sortie (AC: 2)
- [x] Ajouter les imports de modeles necessaires a `create_schema` (AC: 5)
- [x] Ajouter les champs de configuration `media_assets_dir` et `media_studio_dir`
  avec defaults sous `storage/` (AC: 6)
- [x] Ajouter les tests unitaires des invariants et transitions (AC: 1-4)
- [x] Ajouter les tests SQLite base vide/base existante (AC: 5)

## Dev Notes

- Le domaine Atelier est local et ne remplace pas `DownloadJob`.
- Les sorties de telechargement existantes pourront etre referencees comme assets dans
  les stories suivantes, mais cette story peut se limiter a la persistance generique.
- Stockage recommande:
  - `storage/assets/` pour les uploads/imports utilisateur.
  - `storage/studio/` pour les sorties et fichiers de travail d'atelier.
- Ne pas introduire Alembic pour cette story; rester additif avec `Base.metadata.create_all`.
- Ne pas stocker de chemin absolu expose publiquement.
- Les options de job peuvent etre stockees en JSON texte borne pour garder le schema
  extensible.

## Testing Requirements

- Tests unitaires de creation valide/invalide des enums et modeles.
- Tests SQLite de creation de tables sur base vide.
- Tests SQLite depuis une base existante contenant `download_jobs`.
- Tests de non-regression garantissant que les endpoints jobs existants restent
  inchanges.

## References

- `app/models/job.py`
- `app/db/init_db.py`
- `app/core/config.py`
- `app/services/storage_service.py`

## Definition of Done

- Les modeles Atelier sont persistables et testes.
- La configuration de stockage est disponible.
- Le pipeline de telechargement existant ne change pas.
- Les controles qualite cibles passent.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest tests/test_studio_domain.py -q` -> 9 passed
- `uv run pytest tests/test_playlist_domain.py tests/test_playlist_schema.py -q` -> 11 passed
- `uv run pytest -q` -> 96 passed
- `uv run ruff check .` -> all checks passed

### Completion Notes List

- Ajout du domaine persistant `MediaAsset`, `MediaEditJob` et `MediaEditJobInput`.
- Ajout de `MediaEditJobOutput` pour tracer les operations produisant plusieurs sorties.
- Ajout des enums d'origine, type media, operation et statut d'edition.
- Ajout de transitions explicites pour les jobs d'atelier.
- Ajout des repertoires configures `media_assets_dir` et `media_studio_dir`.
- Le schema reste additif et compatible avec une base contenant seulement `download_jobs`.

### File List

- `app/core/config.py`
- `app/db/init_db.py`
- `app/models/__init__.py`
- `app/models/studio.py`
- `tests/test_studio_domain.py`
- `_bmad-output/implementation-artifacts/5-1-socle-domaine-atelier-et-assets-media.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-06-30: Story creee et placee en ready-for-dev.
- 2026-06-30: Socle domaine Atelier implemente et story placee en review.
