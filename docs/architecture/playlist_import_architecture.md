# Architecture cible: Playlist Import & Media Resolution

Status: proposed

## Decision

Ajouter un domaine "playlist import" en amont du pipeline de telechargement actuel, sans
modifier la responsabilite de `MediaDownloader` ni remplacer `JobRunner`.

Le flux cible est:

```text
fichier utilisateur
    |
    v
PlaylistImporter
    |
    v
TrackNormalizer
    |
    v
ImportedPlaylist + Track (SQLite)
    |
    v  action utilisateur
MediaSearchProvider
    |
    v
ResolvedMediaCandidate (SQLite)
    |
    v  selection explicite
PlaylistQueueService / JobSubmissionService
    |
    v
DownloadQueueItem -> DownloadJob -> JobRunner -> MediaDownloader
```

## Frontieres de responsabilite

### Import de listes

Responsable de:

- reconnaitre et parser un format fourni par l'utilisateur;
- conserver l'ordre et les valeurs brutes utiles;
- produire des pistes candidates a la normalisation;
- signaler des erreurs ligne par ligne.

Non responsable de:

- rechercher des medias;
- choisir un candidat;
- telecharger une URL.

Interface cible:

```python
class PlaylistImporter(Protocol):
    key: str

    def import_tracks(
        self,
        content: BinaryIO,
        *,
        filename: str | None,
    ) -> ImportResult: ...
```

Les implementations initiales sont `shazam_csv` et `text`, puis des adaptateurs
d'exports utilisateur Spotify, Deezer et Apple Music. Ces adaptateurs doivent parser des
fichiers fournis par l'utilisateur, pas contourner OAuth, les API ou les controles
d'acces des plateformes. Un importer YouTube Playlist pourra extraire les entrees d'une
liste comme metadonnees, mais il reste distinct du provider de recherche YouTube et ne
doit pas contourner la selection ni la queue de telechargement.

### Normalisation des metadonnees

Responsable de:

- normaliser Unicode et espaces;
- separer artiste, titre et version lorsque les regles sont suffisamment certaines;
- conserver les valeurs brutes;
- versionner les regles appliquees;
- calculer une cle de deduplication conservative.

Non responsable de:

- supprimer automatiquement des mentions ambigues comme `live`, `remix` ou `cover`;
- decider qu'une piste correspond a un resultat media;
- appliquer des regles propres a l'interface.

Une normalisation conservative est preferable a une correction irreversible. Les termes
musicaux pertinents doivent rester disponibles pour la requete de recherche.

### Recherche de media

Responsable de:

- transformer un `Track` en requete provider;
- interroger un fournisseur sans telechargement;
- mapper les reponses vers `ResolvedMediaCandidate`;
- borner le nombre de resultats, la concurrence et le timeout;
- exposer des erreurs provider stables.

Non responsable de:

- creer un `DownloadJob`;
- publier un fichier;
- selectionner silencieusement le premier resultat.

Interface cible:

```python
class MediaSearchProvider(Protocol):
    key: str

    def search(
        self,
        track: Track,
        *,
        limit: int,
    ) -> list[ResolvedMediaCandidate]: ...
```

Le provider YouTube initial peut utiliser `yt-dlp` avec une requete de recherche et
`download=False`. Il doit rester separe de `MediaDownloader`, qui traite une URL deja
selectionnee et applique les options de conversion.

## Guide d'extension

### Ajouter un importer

1. Creer une implementation du protocole `PlaylistImporter` dans
   `app/services/playlist_import/`.
2. Definir une cle stable et explicite, par exemple `spotify_export`.
3. Parser uniquement le fichier fourni par l'utilisateur et retourner des
   `ImportedTrack`; ne pas appeler de provider de recherche et ne pas creer de job.
4. Normaliser via `TrackNormalizer` pour conserver le meme comportement de deduplication,
   de revue, de resolution et de queue.
5. Reporter les lignes invalides avec `ImportIssue` et un code public stable.
6. Enregistrer l'importer dans `create_app` via `PlaylistImporterRegistry.register(...)`.

Le format texte libre montre le contrat minimal: chaque ligne utile devient une piste,
les commentaires et lignes vides sont ignores, et les lignes invalides restent des
issues d'import sans bloquer les pistes valides.

### Ajouter un provider de recherche

1. Creer une implementation du protocole `MediaSearchProvider` dans
   `app/services/media_search/`.
2. Definir une cle stable, par exemple `youtube`, `soundcloud` ou `local_catalog`.
3. Transformer une `TrackQuery` en requete provider et retourner des `SearchCandidate`
   bornes par `limit`.
4. Ne pas creer de `DownloadJob`, ne pas selectionner automatiquement le premier resultat
   et ne pas publier de fichier.
5. Enregistrer le provider dans `create_app` via
   `MediaSearchProviderRegistry.register(...)`.

Un importer YouTube Playlist et le provider de recherche YouTube resolvent deux
problemes differents. Le premier lit une liste en metadonnees locales; le second cherche
des candidats pour une piste deja importee.

### Selection du resultat

Responsable de:

- presenter plusieurs candidats et leurs metadonnees discriminantes;
- enregistrer la selection explicite;
- refuser un candidat absent, obsolete ou appartenant a une autre piste;
- recueillir le format et les options de sortie.

Le score eventuel aide a ordonner les resultats mais ne vaut pas consentement pour un
telechargement automatique.

### Telechargement et conversion

Reste sous la responsabilite de:

- `DownloadJob`;
- `JobRunner`;
- `MediaDownloader`;
- `StorageService`;
- `CleanupService`.

La creation d'un job doit etre extraite dans un `JobSubmissionService` reutilise par la
route URL actuelle et par `PlaylistQueueService`. Cette extraction evitera de dupliquer
validation, persistance, gestion `QUEUE_FULL` et metadonnees initiales.

## Modules cibles

```text
app/
  api/routes/
    jobs.py
    playlists.py
  models/
    job.py
    playlist.py
  schemas/
    job.py
    playlist.py
  services/
    job_submission.py
    playlist_queue.py
    track_normalizer.py
    media_resolution.py
    playlist_import/
      __init__.py
      base.py
      registry.py
      shazam_csv.py
      plain_text.py
    media_search/
      __init__.py
      base.py
      registry.py
      youtube.py
```

Les repertoires sont proposes, pas a creer pendant la phase documentaire.

## Persistence

### Tables proposees

- `imported_playlists`
- `tracks`
- `resolved_media_candidates`
- `download_queue_items`

Relations:

```text
ImportedPlaylist 1 --- n Track
Track            1 --- n ResolvedMediaCandidate
Track            1 --- n DownloadQueueItem
ResolvedCandidate 1 -- n DownloadQueueItem
DownloadQueueItem n -- 0..1 DownloadJob
```

Regles:

- La suppression d'un import ne doit pas supprimer un `DownloadJob`.
- Une piste et ses candidats peuvent etre supprimes en cascade seulement si la
  tracabilite du queue item est preservee ou explicitement detachee.
- `download_job_id` est nullable jusqu'a soumission reussie.
- Une contrainte unique sur `idempotency_key` protege contre les doubles ajouts.
- Les payloads bruts doivent etre bornes; ne pas persister le fichier complet.

### Strategie de migration

`app/db/init_db.py` effectue actuellement des `ALTER TABLE` SQLite additifs. Quatre
nouvelles tables et leurs index restent faisables avec `Base.metadata.create_all`, mais
l'Epic doit declencher une decision explicite:

1. conserver temporairement les migrations additives pour cette tranche; ou
2. introduire Alembic avant les premieres modifications destructives ou relationnelles
   complexes.

La recommandation est d'introduire Alembic au plus tard avant la deuxieme version du
schema playlist. La story 4.1 peut rester additive si elle inclut un test de mise a
niveau depuis la base actuelle.

## API cible

Routes indicatives:

| Methode | Route | Responsabilite |
| --- | --- | --- |
| `POST` | `/api/playlists/import` | Import multipart avec `importer_key`. |
| `GET` | `/api/playlists` | Liste paginee des imports. |
| `GET` | `/api/playlists/{id}` | Resume et compteurs. |
| `GET` | `/api/playlists/{id}/tracks` | Pistes paginees. |
| `POST` | `/api/tracks/{id}/resolve` | Recherche via un provider. |
| `GET` | `/api/tracks/{id}/candidates` | Candidats persistants. |
| `POST` | `/api/tracks/{id}/queue` | Selection et soumission d'un candidat. |

Les routes de jobs existantes restent la source de verite pour l'etat, la pause, la
reprise, le fichier final et la suppression.

## Queue et concurrence

Il existe deux types de travail, a ne pas confondre:

1. resolution de metadonnees via un provider;
2. telechargement/conversion via `JobRunner`.

Pour la premiere iteration, une recherche unitaire peut etre executee hors event loop via
`asyncio.to_thread` ou une fonction synchrone routee correctement. La resolution en lot
necessitera ensuite un orchestrateur borne distinct, mais pas une deuxieme queue de
telechargement.

`DownloadQueueItem` est une entite de tracabilite et d'idempotence. La seule queue
d'execution media reste `JobRunner.queue`.

## Integration UI

L'interface actuelle est une page Jinja avec un grand fichier JavaScript. L'ajout doit:

- creer une section distincte pour l'import de listes;
- conserver le parcours URL comme parcours principal stable;
- paginer les pistes et charger les candidats a la demande;
- reutiliser les composants de statut de job apres soumission;
- fournir des actions clavier et des etats `aria-live`;
- verifier les themes clair et sombre.

Avant une UI de resolution en lot, il est recommande de decouper `app.js` en modules
ES natifs ou, au minimum, en objets fonctionnels clairement delimites. Ce refactoring ne
doit pas etre melange avec la premiere story de domaine.

## Erreurs publiques

Codes proposes:

- `IMPORT_FILE_TOO_LARGE`
- `IMPORT_TOO_MANY_ROWS`
- `IMPORT_FORMAT_UNSUPPORTED`
- `IMPORT_FILE_INVALID`
- `IMPORT_PARTIAL`
- `TRACK_INVALID`
- `SEARCH_PROVIDER_UNKNOWN`
- `SEARCH_PROVIDER_UNAVAILABLE`
- `SEARCH_TIMEOUT`
- `NO_MEDIA_CANDIDATES`
- `CANDIDATE_NOT_FOUND`
- `CANDIDATE_STALE`
- `QUEUE_ITEM_ALREADY_SUBMITTED`

`QUEUE_FULL`, les erreurs de source et les erreurs de conversion existantes restent
gerees par le domaine jobs.

## Logs

Evenements proposes:

- `playlist_import_started`
- `playlist_import_completed`
- `playlist_import_partial`
- `playlist_row_rejected`
- `track_resolution_started`
- `track_resolution_completed`
- `track_resolution_failed`
- `media_candidate_selected`
- `playlist_job_submitted`

Champs contextuels a ajouter au formatter JSON:

- `playlist_id`
- `track_id`
- `importer`
- `provider`
- `candidate_id`
- `queue_item_id`

Ne pas logger le fichier complet, les cookies, les URLs contenant des credentials, ni
les payloads bruts non bornes.

## Configuration proposee

| Variable | Valeur initiale indicative |
| --- | --- |
| `PLAYLIST_IMPORT_MAX_BYTES` | `1048576` |
| `PLAYLIST_IMPORT_MAX_TRACKS` | `500` |
| `MEDIA_SEARCH_PROVIDER` | `youtube` |
| `MEDIA_SEARCH_MAX_CANDIDATES` | `5` |
| `MEDIA_SEARCH_TIMEOUT_SECONDS` | `20` |
| `MEDIA_SEARCH_MAX_CONCURRENT` | `2` |

La limite du middleware `MAX_REQUEST_BODY_BYTES` doit rester superieure ou egale a la
limite d'import, avec un ecart documente pour l'encapsulation multipart.

## Strategie de test

### Tests unitaires

- contrats communs importer/provider;
- dialectes CSV et normalisation Unicode;
- mapping des resultats YouTube;
- calcul de score et ordre deterministe;
- idempotence du queue item;
- mapping des erreurs.

### Tests d'integration

- creation et migration du schema SQLite;
- import multipart -> playlist -> pistes;
- piste -> provider fake -> candidats;
- candidat selectionne -> `DownloadJob` -> `FakeRunner.enqueue`;
- queue pleine et rollback coherent;
- redemarrage de l'application avec donnees importees persistantes;
- non-regression des routes `/api/jobs`.

### Tests manuels

- CSV Shazam reel anonymise;
- affichage de plusieurs centaines de pistes avec pagination;
- clavier, mobile et themes;
- smoke test provider sur des contenus accessibles legalement;
- verification des logs et messages sans donnees sensibles.

## Plan d'integration progressif

### Phase A - Fondation sans UI

- Story 4.1.
- Modeles, interfaces, registres et persistence additive.
- Aucun importer concret ni changement du parcours actuel.

### Phase B - Import local inspectable

- Stories 4.2 et 4.3.
- Shazam CSV, normalisation et affichage des pistes.
- Aucun appel reseau et aucun job cree.

### Phase C - Resolution unitaire

- Story 4.4.
- Provider YouTube mocke en tests, candidats persistants et selection manuelle.
- Pas de traitement automatique de toute la playlist.

### Phase D - Adaptation vers le pipeline existant

- Story 4.5.
- Extraction de `JobSubmissionService`.
- Creation idempotente d'un `DownloadQueueItem` et d'un `DownloadJob`.
- Reutilisation de l'historique et des controles existants.

### Phase E - Lots et exploitation

- Stories 4.6 et 4.7.
- Concurrence bornee, reprise, observabilite, limites et documentation complete.

### Phase F - Validation de l'extensibilite

- Story 4.8.
- Deuxieme importer et guide d'extension.
- Planification ulterieure des exports Spotify, Deezer, Apple Music et YouTube Playlist.

## Compatibilite et non-regression

- Aucun changement de schema existant ne doit rendre `download_jobs` illisible.
- `POST /api/jobs` doit continuer de fonctionner sans connaitre les playlists.
- `MediaDownloader` continue de recevoir une URL unique avec `noplaylist=True`.
- Le nouveau module ne modifie pas les statuts de jobs.
- Le cleanup doit definir explicitement la retention des imports, candidats et queue
  items avant leur mise en production.
- Les sauvegardes doivent inclure les nouvelles tables SQLite sans ajouter de nouveaux
  fichiers persistants obligatoires.

## Note juridique et ethique

Le module est un outil personnel d'import et d'organisation de listes, puis de resolution
de medias disponibles via les sources configurees. Il ne doit pas etre presente comme un
moyen de contourner des protections ou des conditions d'utilisation. L'utilisateur doit
verifier qu'il dispose des droits ou autorisations necessaires pour telecharger,
convertir et conserver chaque contenu.
