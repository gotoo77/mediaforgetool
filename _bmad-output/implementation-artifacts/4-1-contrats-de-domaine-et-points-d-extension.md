# Story 4.1: Contrats de domaine et points d'extension

Status: review

## Story

En tant que mainteneur,
je veux disposer de modeles generiques et de contrats extensibles pour les importers et
search providers,
afin d'ajouter Shazam, YouTube et de futurs adaptateurs sans coupler le domaine a une
plateforme.

## Acceptance Criteria

1. Les modeles internes `Track`, `ImportedPlaylist`, `ResolvedMediaCandidate` et
   `DownloadQueueItem` disposent d'identifiants stables et de champs independants de
   Shazam et YouTube.
2. Les relations entre playlist, pistes, candidats, queue items et `DownloadJob` sont
   persistables dans SQLite avec des index adaptes aux consultations prevues.
3. `PlaylistImporter` expose un identifiant stable et une operation d'import vers un
   resultat generique, sans dependance a FastAPI, SQLAlchemy ou `yt-dlp`.
4. `MediaSearchProvider` expose un identifiant stable et une recherche retournant des
   candidats generiques, sans creer de `DownloadJob`.
5. Des registres permettent de resoudre un importer ou provider par identifiant sans
   ajouter de conditionnelle centrale par plateforme.
6. `DownloadQueueItem` reste une entite de tracabilite et ne cree pas de seconde queue
   d'execution; `JobRunner` demeure la seule queue de telechargement.
7. Les transitions de statut et les invariants des quatre modeles sont documentes dans
   le code et couverts par des tests unitaires.
8. Le schema se cree sur une base vide et se met a niveau depuis le schema actuel ne
   contenant que les tables existantes.
9. Les routes `/api/jobs`, l'UI et le pipeline media existants ne changent pas pendant
   cette story.
10. `rtk uv run pytest -q` et `rtk uv run ruff check .` passent.

## Tasks / Subtasks

- [x] Definir les enums de statut minimaux pour playlist, piste et queue item (AC: 1, 7)
- [x] Implementer les entites persistantes et leurs relations (AC: 1, 2)
- [x] Ajouter les imports de modeles necessaires a la creation du schema (AC: 2, 8)
- [x] Definir les objets de transfert independants de l'ORM pour les importers (AC: 3)
- [x] Definir le protocole `PlaylistImporter` (AC: 3)
- [x] Definir le protocole `MediaSearchProvider` (AC: 4)
- [x] Implementer les registres importer/provider avec erreurs explicites (AC: 5)
- [x] Documenter le role non executable de `DownloadQueueItem` (AC: 6)
- [x] Ajouter les tests unitaires des invariants et registres (AC: 5, 7)
- [x] Ajouter les tests de schema SQLite vide et existant (AC: 2, 8)
- [x] Executer les tests cibles puis la suite complete (AC: 9, 10)

## Dev Notes

### Architecture a respecter

- Le domaine playlist s'insere en amont de `DownloadJob`.
- `MediaDownloader` continue de recevoir une URL unique deja selectionnee.
- `JobRunner.queue` reste l'unique queue d'execution media.
- Aucun importer concret, appel reseau, endpoint ou changement UI n'est attendu dans
  cette story.
- Les contrats d'import et de recherche ne doivent pas importer FastAPI, SQLAlchemy,
  `yt_dlp` ou des objets DOM.
- Les classes ORM peuvent referencer `DownloadJob`, mais les protocoles de services
  doivent utiliser des types de domaine ou objets de transfert.

### Modele minimal

`ImportedPlaylist`:

- `id`, `name`, `importer_key`, `source_filename`
- `status`, `track_count`, `rejected_row_count`, `error_summary`
- `created_at`, `updated_at`

`Track`:

- `id`, `playlist_id`, `position`
- `artist`, `title`, `album`, `isrc`, `duration_seconds`
- `raw_artist`, `raw_title`, `source_payload`, `normalization_version`
- `resolution_status`, `created_at`, `updated_at`

`ResolvedMediaCandidate`:

- `id`, `track_id`, `provider_key`, `provider_media_id`, `source_url`
- `title`, `creator`, `duration_seconds`, `thumbnail_url`
- `rank`, `match_score`, `selected_at`, `created_at`

`DownloadQueueItem`:

- `id`, `track_id`, `candidate_id`, `download_job_id`
- `requested_format`, `requested_height`, `requested_audio_bitrate_kbps`
- `status`, `idempotency_key`, `error_code`, `error_message`
- `created_at`, `submitted_at`

### Statuts initiaux recommandes

- Playlist: `importing`, `ready`, `partial`, `failed`
- Track resolution: `pending`, `searching`, `resolved`, `no_match`, `failed`
- Queue item: `pending`, `submitted`, `rejected`

Ne pas reutiliser `JobStatus` pour ces cycles de vie: ils decrivent des phases
distinctes. Ne pas ajouter de statut de telechargement au queue item; l'etat executable
est lu depuis le `DownloadJob` reference.

### Persistence et migrations

- Nouvelles tables proposees: `imported_playlists`, `tracks`,
  `resolved_media_candidates`, `download_queue_items`.
- Utiliser des cles etrangeres explicites et des contraintes d'unicite pour
  `idempotency_key`.
- Borner les colonnes texte exposees publiquement.
- `source_payload` ne doit jamais contenir le fichier complet.
- Cette story peut rester additive avec `Base.metadata.create_all`.
- Ajouter un test ouvrant une base creee par le schema actuel avant d'appeler
  `create_schema`.
- Ne pas introduire Alembic sans decision separee; documenter toutefois que les futures
  migrations destructives ou complexes devront l'utiliser.

### Organisation de fichiers proposee

- `app/models/playlist.py`
- `app/schemas/playlist.py`
- `app/services/playlist_import/__init__.py`
- `app/services/playlist_import/base.py`
- `app/services/playlist_import/registry.py`
- `app/services/media_search/__init__.py`
- `app/services/media_search/base.py`
- `app/services/media_search/registry.py`
- `tests/test_playlist_domain.py`
- `tests/test_playlist_schema.py`
- `tests/test_provider_registries.py`

Le nom exact des tests peut varier, mais les responsabilites doivent rester separees.

### Erreurs minimales

Les registres doivent produire des erreurs applicatives stables pour:

- importer inconnu;
- provider inconnu;
- enregistrement duplique.

Les erreurs de fichier et provider concret appartiennent aux stories suivantes.

### Securite et ethique

Cette story ne telecharge aucun contenu. Les noms et descriptions doivent rester neutres:
outil personnel d'import, organisation et resolution de listes. Les futures
implementations devront rappeler que l'utilisateur est responsable du respect des droits
applicables aux contenus selectionnes.

## Testing Requirements

### Tests unitaires

- Creation valide de chaque objet de domaine.
- Rejet des identifiants ou champs obligatoires invalides.
- Transitions de statut autorisees et interdites.
- Enregistrement et resolution d'un importer fake.
- Enregistrement et resolution d'un provider fake.
- Rejet d'une cle dupliquee et d'une cle inconnue.
- Verification qu'un provider retourne des candidats sans creer de job.

### Tests d'integration SQLite

- Creation des quatre nouvelles tables sur une base vide.
- Creation du schema depuis une base actuelle contenant `download_jobs`.
- Persistance et relecture des relations.
- Unicite de `idempotency_key`.
- Comportement des suppressions et cles etrangeres documente.

### Non-regression

- Suite complete des tests existants.
- Aucun changement du contrat `CreateJobRequest`.
- Aucun nouvel endpoint enregistre.
- Aucun appel `yt-dlp`, `ffmpeg` ou reseau dans les nouveaux tests.

## References

- `docs/epics/playlist_import_media_resolution.md`
- `docs/architecture/playlist_import_architecture.md`
- `docs/architecture.md`
- `app/models/job.py`
- `app/services/job_runner.py`
- `app/services/media_downloader.py`
- `app/db/init_db.py`

## Definition of Done

- Tous les criteres d'acceptation sont couverts.
- Les quatre modeles et les deux protocoles sont utilisables par les stories suivantes.
- Les registres sont testes avec des implementations fake.
- Le schema existant reste compatible.
- Aucun comportement visible de MediaForgeTool n'a change.
- Les controles qualite complets passent.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_playlist_domain.py tests/test_provider_registries.py -q`
  -> 13 passed
- `rtk uv run pytest -q` -> 82 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run ruff check .` -> all checks passed
- `rtk uv run --isolated --python 3.12 pytest tests/test_playlist_domain.py
  tests/test_playlist_schema.py tests/test_provider_registries.py -q` -> 16 passed

### Completion Notes List

- Ajout de quatre entites ORM generiques et de leurs relations persistantes.
- Ajout de cycles de vie distincts et de transitions explicites.
- Ajout d'objets de transfert immuables et de protocoles independants du web, de l'ORM
  et de `yt-dlp`.
- Ajout de registres extensibles avec erreurs applicatives stables.
- `DownloadQueueItem` trace une future soumission sans executer de travail ni remplacer
  `JobRunner`.
- Le schema reste additif et se cree depuis une base actuelle contenant seulement
  `download_jobs`.
- Aucun endpoint playlist ou track n'est enregistre.

### File List

- `app/core/exceptions.py`
- `app/db/init_db.py`
- `app/models/__init__.py`
- `app/models/playlist.py`
- `app/schemas/playlist.py`
- `app/services/media_search/__init__.py`
- `app/services/media_search/base.py`
- `app/services/media_search/registry.py`
- `app/services/playlist_import/__init__.py`
- `app/services/playlist_import/base.py`
- `app/services/playlist_import/registry.py`
- `tests/test_playlist_domain.py`
- `tests/test_playlist_schema.py`
- `tests/test_provider_registries.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/4-1-contrats-de-domaine-et-points-d-extension.md`

## Change Log

- 2026-06-25: Story preparee et placee en ready-for-dev.
- 2026-06-25: Fondations de domaine implementees et story placee en review.
