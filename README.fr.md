# MediaForgeTool

[English](README.md) | [Français](README.fr.md)

MediaForgeTool est une application FastAPI auto-hébergée permettant de télécharger des
médias publics en MP4 ou MP3. Elle utilise `yt-dlp` pour l’extraction et `ffmpeg` pour
la conversion ou le remuxage.

## Démarrage rapide

### Avec Docker

La méthode la plus simple consiste à utiliser l’image publiée sur GitHub Container
Registry :

```bash
docker run -d \
  --name mediaforgetool \
  --restart unless-stopped \
  -p 8421:8421 \
  -v mediaforgetool-storage:/srv/mediaforgetool/storage \
  -v mediaforgetool-temp:/srv/mediaforgetool/temp \
  ghcr.io/gotoo77/mediaforgetool:latest
```

Ouvrez ensuite `http://localhost:8421` dans votre navigateur.

Commandes utiles :

```bash
# État et journaux
docker ps --filter name=mediaforgetool
docker logs -f mediaforgetool

# Arrêt et redémarrage
docker stop mediaforgetool
docker start mediaforgetool

# Mise à jour
docker pull ghcr.io/gotoo77/mediaforgetool:latest
docker rm -f mediaforgetool
docker run -d \
  --name mediaforgetool \
  --restart unless-stopped \
  -p 8421:8421 \
  -v mediaforgetool-storage:/srv/mediaforgetool/storage \
  -v mediaforgetool-temp:/srv/mediaforgetool/temp \
  ghcr.io/gotoo77/mediaforgetool:latest
```

Les volumes Docker conservent la base SQLite et les fichiers téléchargés lorsque le
conteneur est remplacé.

### Depuis le code source

Sous Ubuntu ou Debian :

```bash
sudo apt-get update
sudo apt-get install -y git curl ffmpeg nodejs
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Sous macOS avec Homebrew :

```bash
brew install git ffmpeg node uv
```

Clonez puis démarrez l’application :

```bash
git clone https://github.com/gotoo77/mediaforgetool.git
cd mediaforgetool
cp .env.example .env
uv sync --dev
uv run python -m app.run --reload
```

Ouvrez `http://127.0.0.1:8421`. Arrêtez le serveur avec `Ctrl+C`.

## Fonctionnalités

- téléchargement MP4 ou MP3 depuis une URL publique ;
- choix du débit MP3 ;
- choix de la résolution MP4 et estimation de taille ;
- téléchargement d’un extrait défini par des marqueurs temporels ;
- création de lots de segments depuis le navigateur ;
- traitement en arrière-plan avec progression ;
- pause et reprise des travaux ;
- historique local et téléchargement du fichier final ;
- nettoyage automatique des sorties expirées ;
- conservation des travaux interrompus ou mis en pause.

MediaForgeTool ne gère pas les comptes utilisateurs, OAuth, le téléchargement direct de
playlists de plateformes, les cookies envoyés par les utilisateurs ni les files
distribuées. Les listes importées sont traitées comme des métadonnées locales et ne
déclenchent aucun téléchargement automatiquement. L’application est conçue pour un seul
processus serveur.

## Prérequis

- Python 3.12 ou supérieur ;
- `ffmpeg` et `ffprobe` accessibles dans le `PATH` ;
- un runtime JavaScript pour certains extracteurs `yt-dlp` ; l’image Docker installe
  Node.js.

Vérification :

```bash
ffmpeg -version
ffprobe -version
node --version
```

Le démarrage échoue avec un message explicite si `ffmpeg` ou `ffprobe` est absent.

## Docker Compose

Pour construire l’image depuis le dépôt et conserver les données dans les dossiers
locaux :

```bash
git clone https://github.com/gotoo77/mediaforgetool.git
cd mediaforgetool
cp .env.example .env
docker compose up --build
```

Consultez l’état du service avec :

```bash
docker compose ps
docker compose logs -f mediaforgetool
```

Arrêt :

```bash
docker compose down
```

Les dossiers `storage/` et `temp/` sont montés hors de l’image. Les bases, sorties,
temporaires et cookies locaux ne sont jamais copiés dans l’image Docker.

## Sauvegarde et restauration

MediaForgeTool stocke la base dans `storage/mediaforgetool.db` et les sorties dans
`storage/jobs`.

Créer une sauvegarde :

```bash
uv run python scripts/storage_backup.py create \
  --output backups/mediaforgetool.tar.gz
```

Restaurer dans un stockage vide :

```bash
uv run python scripts/storage_backup.py restore \
  backups/mediaforgetool.tar.gz \
  --target-storage storage
```

Ajoutez `--force` pour remplacer un stockage existant. Arrêtez l’application avant une
restauration.

## API principale

| Action | Méthode et route |
| --- | --- |
| Santé du processus | `GET /healthz` |
| Inspection d’une source | `POST /api/jobs/inspect` |
| Création d’un travail | `POST /api/jobs` |
| Historique local | `GET /api/jobs` |
| État d’un travail | `GET /api/jobs/{job_id}` |
| Pause | `POST /api/jobs/{job_id}/pause` |
| Reprise | `POST /api/jobs/{job_id}/resume` |
| Téléchargement final | `GET /api/jobs/{job_id}/file` |
| Suppression | `DELETE /api/jobs/{job_id}` |
| Nettoyage de l’historique | `DELETE /api/jobs` |
| Import d’une liste | `POST /api/playlists/import` |

Exemple de création MP3 :

```bash
curl -s http://127.0.0.1:8421/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.invalid/media","format":"mp3","audio_bitrate_kbps":192}'
```

Exemple d’extrait :

```bash
curl -s http://127.0.0.1:8421/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.invalid/media","format":"mp4","segment_start_seconds":60,"segment_end_seconds":120}'
```

Importer un CSV Shazam sans lancer de téléchargement :

```bash
curl -s http://127.0.0.1:8421/api/playlists/import \
  -F importer_key=shazam_csv \
  -F file=@shazam.csv
```

Le CSV doit contenir des colonnes de titre et d’artiste. Les variantes courantes
`Title`, `Track Title`, `Artist` et `Artist Name` sont reconnues. Les lignes invalides
ou dupliquées sont signalées dans la réponse tandis que les pistes valides sont
enregistrées pour une consultation ultérieure. L’import ne recherche aucun média et ne
crée aucun travail de téléchargement.

Importer une liste texte libre via le même endpoint :

```bash
curl -s http://127.0.0.1:8421/api/playlists/import \
  -F importer_key=text \
  -F file=@tracks.txt
```

Chaque ligne non vide et non commentée doit utiliser `Artiste - Titre`. Les lignes qui
commencent par `#` et les lignes vides sont ignorées. Les lignes invalides et les
doublons sont signalés explicitement dans la réponse; les pistes valides utilisent le
même normalizer, le même écran de revue, la même résolution et la même queue que les
imports CSV.

### Étendre les imports et la recherche

Les importers de listes sont enregistrés dans `PlaylistImporterRegistry`. Un nouvel
importer doit exposer une clé stable, être enregistré dans `create_app` et produire
uniquement des métadonnées de pistes. Les futurs supports Spotify, Deezer et Apple Music
doivent être des adaptateurs d’exports fournis par l’utilisateur, pas des contournements
d’API, de comptes ou d’authentification. Un importer YouTube Playlist peut transformer
une playlist en métadonnées locales, mais il reste distinct du provider de recherche
YouTube.

Les providers de recherche sont enregistrés dans `MediaSearchProviderRegistry`. Ils
résolvent une `Track` persistée en candidats sans créer de travaux. Un téléchargement
n’est créé qu’après sélection explicite d’un candidat et ajout à la queue existante.

L’utilisateur reste responsable de vérifier qu’il dispose des droits ou autorisations
nécessaires pour tout média inspecté, téléchargé ou converti avec l’instance.

## Journaux

MediaForgeTool écrit des journaux JSON sur stdout. Chaque entrée contient `timestamp`,
`level`, `logger` et `message`; les événements de requête, de travail et de playlist
peuvent aussi inclure `request_id`, `event`, `job_id`, `playlist_id`, `track_id`,
`candidate_id`, `queue_item_id`, `importer`, `provider`, `status`, `error_code`,
`platform` et `row_number`.

Événements opérationnels courants :

| Événement | Sens |
| --- | --- |
| `app_started` | Démarrage FastAPI terminé. |
| `job_submitted` | Travail accepté par la queue existante. |
| `job_completed` / `job_failed` | Travail terminé ou échoué avec un code public. |
| `playlist_import_completed` / `playlist_import_partial` | Import terminé. |
| `playlist_import_row_rejected` | Ligne rejetée; seuls ligne et code public sont journalisés. |
| `media_search_started` / `media_search_completed` | Résolution lancée ou terminée. |
| `media_search_no_results` / `media_search_failed` | Aucun candidat ou erreur provider. |
| `media_candidate_selected` | Candidat explicitement ajouté à la queue. |

## Configuration

La configuration provient des variables d’environnement et du fichier `.env`. Copiez
`.env.example` avant le premier lancement.

| Variable | Valeur par défaut |
| --- | --- |
| `APP_HOST` | `127.0.0.1` |
| `APP_PORT` | `8421` |
| `ALLOWED_HOSTS` | `*` |
| `MAX_CONCURRENT_JOBS` | `2` |
| `MAX_QUEUE_SIZE` | `32` |
| `PLAYLIST_IMPORT_MAX_BYTES` | `524288` |
| `PLAYLIST_IMPORT_MAX_TRACKS` | `500` |
| `MEDIA_SEARCH_MAX_CANDIDATES` | `5` |
| `MEDIA_RESOLUTION_MAX_CONCURRENCY` | `2` |
| `MAX_OUTPUT_SIZE_MB` | `500` |
| `MAX_MEDIA_DURATION_SECONDS` | `3600` |
| `MP3_BITRATE_KBPS` | `192` |
| `JOB_TIMEOUT_SECONDS` | `1800` |
| `OUTPUT_RETENTION_HOURS` | `24` |
| `TEMP_RETENTION_HOURS` | `2` |
| `YTDLP_SOCKET_TIMEOUT_SECONDS` | `20` |
| `YTDLP_JS_RUNTIME` | `node` |

Ne lancez pas plusieurs workers Uvicorn : chaque processus créerait sa propre file en
mémoire.

## Cookies optionnels

Certaines plateformes peuvent exiger une session authentifiée. MediaForgeTool accepte
uniquement des cookies configurés par l’administrateur de l’instance.

Dans `.env` :

```bash
YTDLP_COOKIES_FILE=secrets/cookies.txt
```

Avec Docker, montez `secrets/` en lecture seule. Les cookies sont des identifiants
sensibles : ne les commitez jamais et renouvelez-les en cas d’exposition.

## Sécurité et limites

- seules les URL HTTP(S) publiques sont acceptées ;
- les adresses privées, loopback et link-local évidentes sont refusées ;
- chaque réponse contient un `X-Request-ID` ;
- les pages et l’API incluent des en-têtes de sécurité navigateur ;
- la taille des corps HTTP est limitée ;
- une exposition publique doit encore utiliser TLS, un reverse proxy et une politique
  réseau limitant les sorties ;
- la compatibilité dépend des évolutions des plateformes et de `yt-dlp`.

## Développement

```bash
uv sync --dev
uv run ruff check .
uv run pytest -q
```

Le pipeline GitHub Actions exécute ces contrôles puis construit les images
`linux/amd64` et `linux/arm64`.

Pour les détails exhaustifs sur l’architecture, les journaux, les en-têtes HTTP et les
contrats API, consultez également la [documentation anglaise](README.md).
