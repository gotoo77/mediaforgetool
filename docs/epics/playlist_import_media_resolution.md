# Epic: Playlist Import & Media Resolution

Status: proposed

## Vision

Permettre a un utilisateur d'importer une liste musicale personnelle, de normaliser ses
metadonnees, de rechercher des medias correspondants via des fournisseurs configurables,
de choisir les bons resultats puis de les envoyer vers le pipeline de telechargement
MP3/MP4 existant.

Le premier parcours cible un export CSV Shazam et une recherche YouTube. L'architecture
doit cependant permettre d'ajouter ensuite des importers texte, Spotify, Deezer, Apple
Music ou YouTube Playlist, ainsi que d'autres fournisseurs de recherche, sans modifier
le coeur du pipeline de telechargement.

## Valeur utilisateur

- Eviter la ressaisie manuelle de chaque artiste et titre.
- Garder le controle sur le resultat media retenu avant tout telechargement.
- Reutiliser l'historique, la pause, la reprise et la conversion deja disponibles.
- Distinguer clairement une piste musicale importee d'une URL media resolue.

## Principes de perimetre

- L'import porte sur des metadonnees de listes, pas sur des fichiers audio.
- Aucun telechargement ne demarre pendant l'import ou la recherche.
- La selection d'un candidat est explicite avant la creation d'un `DownloadJob`.
- Le pipeline existant conserve la responsabilite du telechargement et de la conversion.
- Le MVP reste mono-processus, SQLite et queue memoire bornee.
- Les nouveaux traitements respectent les limites de taille, de debit et de concurrence
  de l'instance.
- L'utilisateur reste responsable du respect des droits applicables aux contenus qu'il
  choisit de telecharger ou convertir.

## Architecture actuelle resumee

MediaForgeTool est un monolithe FastAPI organise par couches:

- `app/api/routes/jobs.py` expose l'inspection, la creation et le cycle de vie des jobs.
- `app/models/job.py` persiste `DownloadJob` et ses statuts dans SQLite.
- `app/services/job_runner.py` gere une queue `asyncio.Queue` bornee et des workers.
- `app/services/media_downloader.py` encapsule `yt-dlp` et `ffmpeg` pour une URL resolue.
- `app/templates/index.html` et `app/static/app.js` portent une UI sans framework.
- `app/db/init_db.py` cree le schema et applique de petites migrations SQLite additives.
- Les tests isolent les frontieres externes avec des fakes et utilisent `TestClient`.
- Les logs JSON exposent notamment `event`, `job_id`, `status`, `error_code` et `platform`.

La nouvelle capacite doit s'inserer avant `POST /api/jobs`: elle transforme une ligne
importee en `Track`, resout des candidats, puis cree un job existant a partir du candidat
choisi.

## Resultats attendus de l'Epic

1. Un domaine generique de pistes et playlists importees.
2. Un registre d'importers extensible, avec Shazam CSV en premier.
3. Un registre de search providers extensible, avec YouTube en premier.
4. Une resolution persistante et inspectable, sans telechargement implicite.
5. Un adaptateur unique vers `DownloadJob` et `JobRunner`.
6. Une UI permettant import, revue, recherche, selection et ajout a la queue.
7. Des limites, logs, erreurs, tests et documentation adaptes au traitement par lots.

## Stories priorisees

### Story 4.1 - Contrats de domaine et points d'extension

Priorite: P0 - fondation

#### Objectif fonctionnel

Definir les modeles internes `Track`, `ImportedPlaylist`, `ResolvedMediaCandidate` et
`DownloadQueueItem`, ainsi que les protocoles `PlaylistImporter` et
`MediaSearchProvider`. Aucun appel reseau ni changement visible dans l'UI n'est requis.

#### Criteres d'acceptation

1. Les quatre modeles ont des identifiants stables et des champs independants de Shazam
   et YouTube.
2. `PlaylistImporter` expose un identifiant de format et une operation d'import vers des
   pistes brutes ou normalisees.
3. `MediaSearchProvider` expose un identifiant et une recherche retournee sous forme de
   candidats generiques.
4. Un registre permet de resoudre un importer ou provider par identifiant sans
   conditionnelle centrale par fournisseur.
5. Les contrats n'importent ni FastAPI, ni `yt_dlp`, ni les classes de l'UI.
6. Les invariants de normalisation et les transitions de statut sont documentes et
   testes.

#### Fichiers probablement impactes

- `app/models/playlist.py`
- `app/schemas/playlist.py`
- `app/services/playlist_import/base.py`
- `app/services/playlist_import/registry.py`
- `app/services/media_search/base.py`
- `app/services/media_search/registry.py`
- `app/models/__init__.py`
- `app/db/init_db.py`
- `tests/test_playlist_domain.py`

#### Risques techniques

- Confondre les dataclasses de transfert avec les entites ORM persistantes.
- Sur-modeliser trop tot les particularites de chaque plateforme.
- Introduire des statuts redondants ou contradictoires avec `JobStatus`.
- Continuer les migrations SQLite manuelles sans strategie lorsque le schema grandit.

#### Strategie de test

- Tests unitaires des validations et transitions de statuts.
- Tests de contrat communs applicables a chaque importer et provider.
- Test de creation du schema sur une base vide.
- Test de migration additive depuis une base ne contenant que `download_jobs`.

### Story 4.2 - Import et normalisation d'un CSV Shazam

Priorite: P0 - premiere valeur utilisateur

#### Objectif fonctionnel

Importer un CSV Shazam, detecter ses colonnes utiles, normaliser artiste et titre, puis
persister une playlist et ses pistes sans effectuer de recherche reseau.

#### Criteres d'acceptation

1. Un fichier CSV Shazam UTF-8 valide produit une `ImportedPlaylist` et des `Track`.
2. Le parseur accepte les variantes documentees de noms de colonnes Shazam.
3. Les espaces, valeurs vides, marqueurs explicites de version et doublons exacts sont
   traites de maniere deterministe.
4. Chaque piste conserve la ligne source et les valeurs brutes utiles au diagnostic.
5. Les lignes invalides n'annulent pas tout l'import; elles sont comptees et exposees
   avec un message actionnable.
6. La taille du fichier, le nombre de lignes et le type de fichier sont limites.
7. Aucun `DownloadJob` n'est cree pendant l'import.

#### Fichiers probablement impactes

- `app/services/playlist_import/shazam_csv.py`
- `app/services/track_normalizer.py`
- `app/api/routes/playlists.py`
- `app/schemas/playlist.py`
- `app/models/playlist.py`
- `app/core/config.py`
- `app/core/exceptions.py`
- `app/main.py`
- `tests/fixtures/shazam/*.csv`
- `tests/test_shazam_csv_importer.py`
- `tests/test_playlists_api.py`

#### Risques techniques

- Variantes de dialecte CSV, encodage BOM, separateurs et colonnes localisees.
- Normalisation trop agressive supprimant une information musicale pertinente.
- Upload entierement charge en memoire ou contournement de la limite HTTP existante.
- Donnees formulees pour provoquer une injection CSV lors d'un futur re-export.

#### Strategie de test

- Fixtures minimales, BOM, virgule, point-virgule, champs quotes et Unicode.
- Tests de lignes incompletes, doublons et fichier depassant les limites.
- Test API multipart avec importer fake ou fichier reel court.
- Test garantissant l'absence de job et d'appel provider apres import.

### Story 4.3 - Consultation d'une playlist et revue des pistes

Priorite: P0 - premiere iteration UI

#### Objectif fonctionnel

Afficher la playlist importee, ses pistes normalisees, les avertissements de parsing et
leur etat de resolution afin que l'utilisateur puisse verifier le contenu avant toute
recherche.

#### Criteres d'acceptation

1. L'API liste les imports recents et retourne le detail pagine d'une playlist.
2. L'UI propose un espace "Import de liste" distinct du formulaire URL existant.
3. Les pistes montrent au minimum artiste, titre, album si disponible et etat courant.
4. Les erreurs de ligne sont visibles sans exposer de trace interne.
5. L'historique et le formulaire de telechargement actuels restent fonctionnels.
6. Le rechargement de la page ne fait pas perdre l'import persiste.

#### Fichiers probablement impactes

- `app/api/routes/playlists.py`
- `app/schemas/playlist.py`
- `app/templates/index.html`
- `app/static/app.js`
- `app/static/app.css`
- `app/main.py`
- `tests/test_playlists_api.py`
- tests UI DOM ou tests navigateur a introduire si l'outillage est retenu

#### Risques techniques

- Alourdir le fichier `app.js`, deja volumineux, sans separer les responsabilites.
- Rendre des centaines de lignes dans le DOM sans pagination.
- Melanger l'historique des imports avec l'historique des telechargements.
- Introduire des regressions d'accessibilite clavier ou de contraste.

#### Strategie de test

- Tests API de pagination, playlist absente et serialisation des erreurs.
- Test de non-regression de la page et des assets versions.
- Tests manuels clavier, mobile et themes clair/sombre.
- Si le module UI grandit, ajouter un runner navigateur leger avant les interactions
  complexes.

### Story 4.4 - Provider de recherche YouTube

Priorite: P0 - resolution initiale

#### Objectif fonctionnel

Rechercher des candidats YouTube pour une piste normalisee sans telecharger le media, et
persister un nombre limite de resultats ordonnes avec leurs metadonnees.

#### Criteres d'acceptation

1. Le provider construit une requete deterministe a partir de l'artiste et du titre.
2. Il retourne des `ResolvedMediaCandidate` avec URL, titre, chaine/artiste, duree,
   miniature, provider et score/rang.
3. La recherche utilise `yt-dlp` en mode extraction sans telechargement ou un adaptateur
   equivalent, sans reintroduire cette logique dans la route HTTP.
4. Les resultats sont limites et persistes par piste.
5. Les erreurs d'authentification, absence de resultat, timeout et indisponibilite sont
   mappees vers des codes publics propres.
6. Une nouvelle recherche remplace ou versionne proprement les anciens candidats.
7. Aucune recherche ne cree de `DownloadJob`.

#### Fichiers probablement impactes

- `app/services/media_search/youtube.py`
- `app/services/media_search/base.py`
- `app/services/media_resolution.py`
- `app/api/routes/playlists.py`
- `app/core/config.py`
- `app/core/exceptions.py`
- `app/core/logging.py`
- `tests/test_youtube_search_provider.py`
- `tests/test_media_resolution.py`
- `tests/test_playlists_api.py`

#### Risques techniques

- Dependance aux changements YouTube et `yt-dlp`.
- Faux positifs: live, cover, remix, karaoke ou video longue.
- Latence et rate limiting lors d'une recherche sur beaucoup de pistes.
- Recherche synchrone bloquant l'event loop ou saturant les workers.
- Reutilisation incorrecte de `MediaDownloader.inspect`, concu pour une URL connue.

#### Strategie de test

- Mock strict de la frontiere `yt-dlp`; aucun reseau dans la suite automatisee.
- Tests de mapping, classement, duree inconnue et resultat vide.
- Tests de timeout, erreur fournisseur et limitation du nombre de candidats.
- Smoke test manuel optionnel sur une piste librement accessible.

### Story 4.5 - Selection d'un candidat et ajout a la queue existante

Priorite: P0 - tranche verticale MVP

#### Objectif fonctionnel

Permettre a l'utilisateur de choisir un candidat resolu, un format MP3/MP4 et ses options,
puis creer un `DownloadJob` et l'enfiler dans le `JobRunner` existant.

#### Criteres d'acceptation

1. Un candidat doit etre selectionne explicitement avant l'ajout a la queue.
2. Le service d'orchestration reutilise la meme validation et la meme creation de job
   que `POST /api/jobs`, sans dupliquer les regles metier.
3. `DownloadQueueItem` reference le `Track`, le candidat et le `DownloadJob` cree.
4. Les limites de queue et erreurs `QUEUE_FULL` restent identiques au parcours URL.
5. La piste affiche le statut du job associe et un lien vers l'historique existant.
6. Un double clic ou une requete repetee ne cree pas deux jobs par inadvertance.
7. Pause, reprise, suppression, retention et telechargement final continuent d'utiliser
   les endpoints de jobs existants.

#### Fichiers probablement impactes

- `app/services/job_submission.py` a extraire depuis `app/api/routes/jobs.py`
- `app/services/playlist_queue.py`
- `app/api/routes/jobs.py`
- `app/api/routes/playlists.py`
- `app/models/playlist.py`
- `app/schemas/playlist.py`
- `app/static/app.js`
- `app/templates/index.html`
- `tests/test_job_submission.py`
- `tests/test_playlist_queue.py`
- `tests/test_playlists_api.py`
- `tests/test_jobs_api.py`

#### Risques techniques

- Dupliquer la creation de `DownloadJob` et faire diverger les deux parcours.
- Course entre creation du queue item, commit du job et `runner.enqueue`.
- Idempotence insuffisante et doublons utilisateur.
- Suppression d'une playlist qui casserait la tracabilite d'un job encore actif.

#### Strategie de test

- Tests unitaires du service commun de soumission avec `FakeRunner`.
- Test d'integration import -> candidat -> selection -> job `queued`.
- Tests queue pleine, candidat absent, deja enfile et format invalide.
- Suite complete des tests de jobs pour garantir les non-regressions.

### Story 4.6 - Resolution et ajout en lot controles

Priorite: P1 - apres validation du parcours unitaire

#### Objectif fonctionnel

Permettre de lancer la recherche ou l'ajout a la queue sur une selection de pistes, avec
progression, limites et reprise explicites, sans contourner la queue bornee existante.

#### Criteres d'acceptation

1. L'utilisateur selectionne les pistes a traiter; aucune action globale implicite.
2. Le nombre de recherches concurrentes est configurable et borne.
3. L'ajout en lot s'arrete proprement lorsque la queue de telechargement est pleine et
   indique les pistes non ajoutees.
4. La progression distingue import, recherche, attente de selection et telechargement.
5. Les operations sont idempotentes et reprenables apres rechargement de page.
6. Une erreur de piste n'annule pas les autres pistes.

#### Fichiers probablement impactes

- `app/services/media_resolution.py`
- `app/services/playlist_queue.py`
- `app/core/config.py`
- `app/api/routes/playlists.py`
- `app/static/app.js`
- `app/static/app.css`
- `tests/test_media_resolution.py`
- `tests/test_playlist_queue.py`
- `tests/test_playlists_api.py`

#### Risques techniques

- Confondre la queue de resolution et la queue de telechargement.
- Rafales de requetes vers le provider et blocage de l'instance.
- Interface difficile a comprendre avec plusieurs niveaux de progression.
- Etat partiellement persiste lors d'un redemarrage.

#### Strategie de test

- Provider fake lent, partiellement en erreur et rate-limite.
- Tests des bornes de concurrence et de l'arret sur queue pleine.
- Test de reprise apres recreation de l'application.
- Test d'un lot melant pistes resolues, sans resultat et deja enfilees.

### Story 4.7 - Observabilite, erreurs et limites d'exploitation

Priorite: P1 - necessaire avant exposition publique

#### Objectif fonctionnel

Rendre les imports et resolutions diagnosticables avec des codes d'erreur stables, des
logs correles et des limites configurables.

#### Criteres d'acceptation

1. Les logs incluent selon le contexte `playlist_id`, `track_id`, `provider`,
   `importer`, `candidate_id`, `job_id` et `error_code`.
2. Des evenements documentes couvrent import termine, ligne rejetee, recherche lancee,
   recherche terminee, candidat selectionne et job soumis.
3. L'API ne renvoie ni trace, ni requete sensible, ni contenu complet du fichier.
4. Les limites de taille, lignes, candidats, concurrence et timeout sont configurees.
5. Les erreurs publiques distinguent fichier invalide, importer inconnu, provider
   indisponible, aucun resultat et queue pleine.
6. La documentation rappelle les responsabilites de l'utilisateur concernant les
   droits applicables.

#### Fichiers probablement impactes

- `app/core/logging.py`
- `app/core/config.py`
- `app/core/exceptions.py`
- `app/api/routes/playlists.py`
- `.env.example`
- `README.md`
- `README.fr.md`
- `tests/test_logging.py`
- `tests/test_playlists_api.py`

#### Risques techniques

- Logs trop volumineux pour les grandes listes.
- Exposition accidentelle des noms de fichiers, requetes ou donnees brutes.
- Limites incoherentes entre middleware HTTP et service d'import.
- Messages traduits uniquement dans l'UI et non stables pour l'API.

#### Strategie de test

- Tests du formatter JSON avec les nouveaux champs.
- Tests de chaque code d'erreur et statut HTTP.
- Tests aux limites exactes de taille, lignes et candidats.
- Revue manuelle des logs pour verifier l'absence de contenu sensible.

### Story 4.8 - Importer texte libre et guide d'extension

Priorite: P2 - preuve d'extensibilite

#### Objectif fonctionnel

Ajouter un deuxieme importer simple (`Artiste - Titre` par ligne) et documenter la
creation d'importers et providers futurs. Cette story valide que Shazam et YouTube ne
sont pas codes en dur dans le domaine ou l'API.

#### Criteres d'acceptation

1. Le meme endpoint accepte `importer=text` et produit les memes `Track`.
2. Les lignes vides, commentaires et lignes invalides sont gerees explicitement.
3. Aucun changement n'est requis dans le normaliseur, la resolution ou la queue.
4. Un guide indique comment enregistrer un importer ou provider.
5. Spotify, Deezer et Apple Music sont documentes comme adaptateurs d'exports fournis
   par l'utilisateur, sans promettre d'acces API ou de contournement d'authentification.
6. YouTube Playlist est traite comme un importer de metadonnees distinct du provider de
   recherche.

#### Fichiers probablement impactes

- `app/services/playlist_import/plain_text.py`
- `app/services/playlist_import/registry.py`
- `docs/architecture/playlist_import_architecture.md`
- `README.md`
- `README.fr.md`
- `tests/test_plain_text_importer.py`
- tests de contrat importers

#### Risques techniques

- Format libre ambigu lorsque l'artiste ou le titre contient un tiret.
- Couplage residuel a des colonnes Shazam.
- Confusion entre import de playlist YouTube et recherche YouTube.
- Integrations futures soumises aux conditions d'utilisation des plateformes.

#### Strategie de test

- Reutiliser la suite de contrat de `PlaylistImporter`.
- Fixtures texte Unicode, commentaires, separateurs ambigus et lignes invalides.
- Test prouvant qu'un importer enregistre est disponible sans modifier la route.
- Revue du guide avec une implementation fake minimale.

## Modele de donnees interne minimal

Les noms ci-dessous decrivent le domaine cible. L'implementation pourra utiliser des
classes ORM pour la persistence et des schemas Pydantic pour l'API, mais les invariants
doivent rester identiques.

### Track

| Champ | Type | Description |
| --- | --- | --- |
| `id` | UUID/string | Identifiant stable de la piste importee. |
| `playlist_id` | UUID/string | Playlist d'origine. |
| `position` | int | Ordre dans la liste source. |
| `artist` | string | Artiste normalise. |
| `title` | string | Titre normalise. |
| `album` | string nullable | Album normalise si disponible. |
| `isrc` | string nullable | Identifiant musical lorsqu'il est fourni. |
| `duration_seconds` | int nullable | Duree connue dans la liste source. |
| `raw_artist` | string nullable | Valeur avant normalisation. |
| `raw_title` | string nullable | Valeur avant normalisation. |
| `source_payload` | JSON/text nullable | Champs source utiles et bornes pour diagnostic. |
| `normalization_version` | string | Version des regles appliquees. |
| `resolution_status` | enum | `pending`, `searching`, `resolved`, `no_match`, `failed`. |
| `created_at`, `updated_at` | datetime | Audit local. |

### ImportedPlaylist

| Champ | Type | Description |
| --- | --- | --- |
| `id` | UUID/string | Identifiant de l'import. |
| `name` | string | Nom affiche, fourni ou derive du fichier. |
| `importer_key` | string | `shazam_csv`, `plain_text`, etc. |
| `source_filename` | string nullable | Nom nettoye, sans chemin local. |
| `status` | enum | `importing`, `ready`, `partial`, `failed`. |
| `track_count` | int | Pistes valides. |
| `rejected_row_count` | int | Lignes ignorees ou invalides. |
| `error_summary` | string nullable | Resume public borne. |
| `created_at`, `updated_at` | datetime | Audit local. |

### ResolvedMediaCandidate

| Champ | Type | Description |
| --- | --- | --- |
| `id` | UUID/string | Identifiant local du candidat. |
| `track_id` | UUID/string | Piste concernee. |
| `provider_key` | string | `youtube` initialement. |
| `provider_media_id` | string nullable | Identifiant stable chez le provider. |
| `source_url` | string | URL publique validee avant soumission. |
| `title` | string | Titre retourne par le provider. |
| `creator` | string nullable | Chaine, auteur ou artiste retourne. |
| `duration_seconds` | int nullable | Duree retournee. |
| `thumbnail_url` | string nullable | Miniature distante. |
| `rank` | int | Ordre du provider. |
| `match_score` | float nullable | Score explicable, non decision automatique. |
| `selected_at` | datetime nullable | Selection utilisateur. |
| `created_at` | datetime | Audit local. |

### DownloadQueueItem

| Champ | Type | Description |
| --- | --- | --- |
| `id` | UUID/string | Identifiant d'orchestration. |
| `track_id` | UUID/string | Piste importee. |
| `candidate_id` | UUID/string | Candidat choisi. |
| `download_job_id` | UUID/string nullable | FK vers `DownloadJob` apres soumission. |
| `requested_format` | enum | `mp3` ou `mp4`. |
| `requested_height` | int nullable | Option MP4. |
| `requested_audio_bitrate_kbps` | int nullable | Option MP3. |
| `status` | enum | `pending`, `submitted`, `rejected`. |
| `idempotency_key` | string | Protection contre les doubles soumissions. |
| `error_code`, `error_message` | string nullable | Echec de soumission public. |
| `created_at`, `submitted_at` | datetime | Audit local. |

`DownloadQueueItem` ne remplace pas `DownloadJob` et n'est pas une nouvelle queue
d'execution. Il fournit la tracabilite entre playlist, piste, candidat choisi et job
existant.

## Premiere iteration realiste

La premiere tranche verticale doit rester volontairement unitaire:

1. Importer un CSV Shazam borne.
2. Normaliser et persister les pistes.
3. Afficher les pistes detectees et les erreurs de lignes.
4. Sur action utilisateur, rechercher une piste sur YouTube.
5. Afficher au plus cinq candidats.
6. Permettre la selection d'un candidat.
7. Choisir MP3/MP4 et ajouter ce candidat a la queue existante.
8. Suivre ensuite le `DownloadJob` dans l'historique actuel.

Cette iteration correspond aux stories 4.1 a 4.5. Elle exclut la resolution automatique
de toute la liste, le choix automatique du "meilleur" resultat, les APIs OAuth de
plateformes musicales et toute queue distribuee.

## Definition of Done de l'Epic

- Les stories P0 sont terminees et les stories P1 necessaires a l'exploitation sont
  acceptees ou explicitement reportees.
- Les fonctions actuelles URL, segments, MP3/MP4, pause, reprise et historique passent
  leurs tests de non-regression.
- Les frontieres import, normalisation, recherche, selection et telechargement sont
  visibles dans le code et testables independamment.
- Au moins deux importers passent la meme suite de contrat avant de declarer
  l'extensibilite validee.
- Les appels reseau sont mocks dans la suite automatisee.
- La documentation utilisateur couvre le CSV Shazam, la revue des candidats, les
  limites et la responsabilite juridique de l'utilisateur.
