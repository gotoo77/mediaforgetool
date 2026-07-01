# MediaForgeTool

[English](README.md) | [Français](README.fr.md)

MediaForgeTool is a self-hosted FastAPI MVP for downloading public media as MP4 or MP3.
It delegates extraction to `yt-dlp` and conversion or remux work to `ffmpeg`.

## Quick start

### With Docker

The simplest way to run MediaForgeTool is with Docker:

```bash
docker run -d \
  --name mediaforgetool \
  --restart unless-stopped \
  -p 8421:8421 \
  -v mediaforgetool-storage:/srv/mediaforgetool/storage \
  -v mediaforgetool-temp:/srv/mediaforgetool/temp \
  ghcr.io/gotoo77/mediaforgetool:latest
```

Open `http://localhost:8421` in a browser.

Useful commands:

```bash
# View status and logs
docker ps --filter name=mediaforgetool
docker logs -f mediaforgetool

# Stop and restart the application
docker stop mediaforgetool
docker start mediaforgetool

# Update to the latest published image
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

The named volumes preserve the SQLite database and downloaded files when the container
is replaced.

### From source

Install the required system tools.

Ubuntu or Debian:

```bash
sudo apt-get update
sudo apt-get install -y git curl ffmpeg nodejs
curl -LsSf https://astral.sh/uv/install.sh | sh
```

macOS with Homebrew:

```bash
brew install git ffmpeg node uv
```

Clone and start the application:

```bash
git clone https://github.com/gotoo77/mediaforgetool.git
cd mediaforgetool
cp .env.example .env
uv sync --dev
uv run python -m app.run --reload
```

Open `http://127.0.0.1:8421` in a browser. Stop the development server with `Ctrl+C`.
The SQLite database, downloaded files and temporary files are stored under `storage/`
and `temp/`.

See [Local run](#local-run) and [Docker](#docker) for advanced configuration, Compose
and instance-level cookies.

## Scope

Phase 1 includes:

- one URL field and MP4/MP3 choice
- MP3 bitrate presets
- MP4 resolution presets and result-size estimates when the source exposes format sizes
- optional media segment downloads, including suggested segments for long media
- browser-created segment batches, implemented as individual background jobs
- a local Media Studio for simple audio/video edits on known assets:
  replace audio, remove audio, extract audio, split in two and concatenate audio or video
- background download jobs with polling progress
- pause and resume controls for queued or running jobs
- minimal global local history with deletion controls
- final file download
- metadata captured when `yt-dlp` exposes title, platform, thumbnail and duration
- automatic cleanup for temporary files and expired outputs, while preserving resumable paused or interrupted jobs

It intentionally does not include accounts, OAuth, playlists, a distributed queue or
user-supplied cookies. Batch work is limited to segment jobs created by the browser for
one inspected source.

## Architecture

```text
app/api/        HTTP routes and page handlers
app/core/       configuration, logging and application errors
app/db/         SQLAlchemy engine and schema bootstrap
app/models/     persisted download jobs and Media Studio assets
app/schemas/    request and response contracts
app/services/   yt-dlp integration, runner, storage, cleanup and URL guard
app/static/     browser JavaScript and CSS
app/templates/  Jinja page
```

`POST /api/jobs` persists a job and pushes its identifier into a bounded in-process
queue. Worker tasks run blocking `yt-dlp` work outside the FastAPI event loop, update
SQLite with progress and publish only the final artifact into `storage/jobs`.

Studio jobs run `ffmpeg` synchronously in the API process for the current MVP and publish
their outputs under `storage/studio`. The same retention settings clean up expired
Studio outputs and old orphan Studio directories.

The MVP is designed for one application process. Running multiple Uvicorn workers would
create multiple memory queues and is outside the Phase 1 model.

## Requirements

- Python 3.12+
- `ffmpeg` and `ffprobe` on `PATH`
- a JavaScript runtime for `yt-dlp` extractors that require one; Docker installs `nodejs`

## Local run

```bash
cp .env.example .env
uv sync --dev
uv run python -m app.run --reload
```

Open the local app at `http://127.0.0.1:8421` with the default `.env`.
Override `APP_HOST` and `APP_PORT` when another bind address or port is needed.

The host `python3` version is not used by the `uv` commands when `uv` provisions a
compatible Python environment for this project.

## Manual smoke test

Start the app locally, then verify that the process responds without touching the media
pipeline:

```bash
curl -s http://127.0.0.1:8421/healthz
```

Inspect a public media URL before creating a job:

```bash
curl -s http://127.0.0.1:8421/api/jobs/inspect \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.invalid/media"}'
```

Create an MP3 job:

```bash
curl -s http://127.0.0.1:8421/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.invalid/media","format":"mp3"}'
```

Create an MP3 job with an explicit bitrate:

```bash
curl -s http://127.0.0.1:8421/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.invalid/media","format":"mp3","audio_bitrate_kbps":320}'
```

Create an MP4 job with a resolution preset:

```bash
curl -s http://127.0.0.1:8421/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.invalid/media","format":"mp4","resolution":720}'
```

Create a bounded segment job:

```bash
curl -s http://127.0.0.1:8421/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.invalid/media","format":"mp3","segment_start_seconds":60,"segment_end_seconds":120}'
```

Poll the job returned by either create call, then download the completed output:

```bash
curl -s http://127.0.0.1:8421/api/jobs/<job_id>
curl -L -o mediaforgetool-output.bin http://127.0.0.1:8421/api/jobs/<job_id>/file
```

Pause or resume a job:

```bash
curl -s -X POST http://127.0.0.1:8421/api/jobs/<job_id>/pause
curl -s -X POST http://127.0.0.1:8421/api/jobs/<job_id>/resume
```

The automated tests mock the platform boundary. This manual smoke test depends on the
current behavior of the source platform, `yt-dlp`, `ffmpeg`, the optional JavaScript
runtime and any instance-level cookies configured for the deployment.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

The compose service mounts `storage/` and `temp/` so SQLite, outputs and transient job
files stay outside the image.
It also declares a lightweight healthcheck against `/healthz`, so container status can
be inspected without triggering `yt-dlp`, SQLite job queries or media work:

```bash
docker compose ps
```

To run the image without Compose, keep storage, temp files and optional cookies mounted
outside the container:

```bash
docker build -t mediaforgetool .
docker run --rm \
  --env-file .env \
  -e APP_HOST=0.0.0.0 \
  -p 8421:8421 \
  -v "$PWD/storage:/srv/mediaforgetool/storage" \
  -v "$PWD/temp:/srv/mediaforgetool/temp" \
  -v "$PWD/secrets:/srv/mediaforgetool/secrets:ro" \
  mediaforgetool
```

The image declares the same `/healthz` healthcheck for `docker run` deployments.
Runtime directories are created empty during the image build; local databases, outputs,
temporary files and cookies are intentionally excluded from the Docker build context.

### Published container image

GitHub Actions tests the application and publishes multi-architecture images for
`linux/amd64` and `linux/arm64` to GitHub Container Registry. Pull the current `main`
image with:

```bash
docker pull ghcr.io/gotoo77/mediaforgetool:latest
```

Run it with persistent Docker volumes:

```bash
docker run -d \
  --name mediaforgetool \
  --restart unless-stopped \
  -e APP_HOST=0.0.0.0 \
  -p 8421:8421 \
  -v mediaforgetool-storage:/srv/mediaforgetool/storage \
  -v mediaforgetool-temp:/srv/mediaforgetool/temp \
  ghcr.io/gotoo77/mediaforgetool:latest
```

Pushes to `main` publish `latest` and a commit-SHA tag. Git tags such as `v1.0.0`
also publish versioned image tags such as `1.0.0` and `1.0`.

## Backup and restore

MediaForgeTool persists SQLite state in `storage/mediaforgetool.db`, completed download
outputs under `storage/jobs`, source assets under `storage/assets` and Studio outputs
under `storage/studio`. Create a backup archive with:

```bash
uv run python scripts/storage_backup.py create --output backups/mediaforgetool.tar.gz
```

Restore into an empty storage directory with:

```bash
uv run python scripts/storage_backup.py restore backups/mediaforgetool.tar.gz --target-storage storage
```

If the target storage directory already contains files, pass `--force` to replace it.
Stop the application before restoring so the running process does not keep an old
SQLite connection open.

## API

Health check:

```http
GET /healthz
```

Create a job:

```http
POST /api/jobs
Content-Type: application/json

{"url":"https://example.invalid/media","format":"mp3"}
```

Inspect a source before creating a job:

```http
POST /api/jobs/inspect
Content-Type: application/json

{"url":"https://example.invalid/media"}
```

For MP4, job creation can include a `resolution` preset such as `720`. Inspection
returns the available presets and estimated sizes. MP3 estimates use the configured
output bitrate and media duration, so every size remains approximate.

For MP3, job creation can include `audio_bitrate_kbps` with one of `128`, `192`, `256`
or `320`. Any job can include `segment_start_seconds` and `segment_end_seconds` together
to download only a bounded excerpt. Segment duration is checked against the configured
maximum media duration, and real source duration is checked again during extraction when
the platform exposes it.

Inspection can return `segment_suggestions` for sources longer than the configured media
duration limit. The browser can use these suggestions or custom markers to create a
small batch of independent segment jobs for the same inspected source.

Read status:

```http
GET /api/jobs/{job_id}
```

List recent local history:

```http
GET /api/jobs?limit=20
```

Pause a queued or running job:

```http
POST /api/jobs/{job_id}/pause
```

Resume an interrupted, failed or paused job:

```http
POST /api/jobs/{job_id}/resume
```

Delete one inactive job and its retained files:

```http
DELETE /api/jobs/{job_id}
```

Clear inactive local history while skipping active or paused jobs:

```http
DELETE /api/jobs
```

Download a completed output:

```http
GET /api/jobs/{job_id}/file
```

Studio assets and jobs:

```http
GET /api/studio/assets
GET /api/studio/assets/{asset_id}/inspect
POST /api/studio/jobs
GET /api/studio/jobs/{job_id}
GET /api/studio/jobs/{job_id}/outputs/{position}/file
```

Supported Studio operations are `replace_audio`, `remove_audio`, `extract_audio`,
`split_media`, `concat_audio` and `concat_video`. Audio concat re-encodes to MP3 or M4A.
Video concat uses the fast FFmpeg concat path with `-c copy`; source videos must already
be compatible in container, codecs and dimensions when those properties are known.

## Logs

MediaForgeTool writes JSON logs to stdout. Every entry includes `timestamp`, `level`,
`logger` and `message`; request and job events can also include `request_id`, `event`,
`job_id`, `status`, `error_code` and `platform`.

Common operational events include:

| Event | Meaning |
| --- | --- |
| `app_started` | FastAPI startup completed and background services started. |
| `queued_job_recovered` | A queued job was recovered during startup. |
| `job_completed` | A media job published its final output. |
| `job_failed` | A media job failed with an application error code. |
| `studio_asset_imported` | A Studio output asset was registered in local storage. |
| `studio_probe_failed` | A Studio asset could not be inspected. |
| `studio_job_started` | A Studio job was accepted by the API. |
| `studio_job_processing` | A Studio job entered FFmpeg processing. |
| `studio_job_completed` | A Studio job published its output assets. |
| `studio_job_failed` | A Studio job failed with a public error code. |
| `studio_job_cleaned` | Cleanup removed an expired Studio job directory and records. |
| `stale_directory_removed` | Cleanup removed an expired temporary or output directory. |

Use `LOG_LEVEL` to adjust verbosity.
Every HTTP response includes `X-Request-ID`. If an incoming request already has a
printable `X-Request-ID` up to 128 characters, MediaForgeTool preserves it; otherwise it
generates a new identifier.

## HTTP hardening

Every page and API response includes baseline browser hardening headers:

| Header | Value |
| --- | --- |
| `Content-Security-Policy` | Allows same-origin assets and HTTPS/data thumbnails, blocks object embedding and framing. |
| `Permissions-Policy` | Disables camera, microphone and geolocation. |
| `Referrer-Policy` | `no-referrer` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-Request-ID` | Preserved from the request or generated per response for log correlation. |

These headers are application-level defaults. A public deployment should still use a
reverse proxy or network policy for TLS, request-size limits and egress restrictions.
MediaForgeTool also rejects requests whose `Content-Length` exceeds
`MAX_REQUEST_BODY_BYTES`; this protects the JSON API surface, not reverse-proxy upload
or connection limits.
Set `ALLOWED_HOSTS` to a comma-separated host allowlist, such as
`mediaforgetool.example.com,localhost`, when the instance is published behind a reverse
proxy. The default `*` keeps local development permissive.

## Configuration

Configuration is loaded from environment variables and `.env`. Start from
`.env.example`.

Before starting the app, verify the required binaries:

```bash
ffmpeg -version
ffprobe -version
```

If a JavaScript runtime is configured for `yt-dlp`, verify it as well:

```bash
node --version
```

Startup fails with an explicit `Required binary is unavailable: <name>` error when
`ffmpeg` or `ffprobe` is not discoverable from `PATH` or the configured binary name.

Important limits:

| Variable | Default |
| --- | --- |
| `APP_HOST` | `127.0.0.1` |
| `APP_PORT` | `8421` |
| `ALLOWED_HOSTS` | `*` |
| `MAX_CONCURRENT_JOBS` | `2` |
| `MAX_QUEUE_SIZE` | `32` |
| `JOB_CREATE_RATE_LIMIT_COUNT` | `10` |
| `JOB_CREATE_RATE_LIMIT_WINDOW_SECONDS` | `60` |
| `MAX_REQUEST_BODY_BYTES` | `1048576` |
| `MAX_OUTPUT_SIZE_MB` | `500` |
| `MAX_MEDIA_DURATION_SECONDS` | `3600` |
| `MP3_BITRATE_KBPS` | `192` |
| `JOB_TIMEOUT_SECONDS` | `1800` |
| `OUTPUT_RETENTION_HOURS` | `24` |
| `TEMP_RETENTION_HOURS` | `2` |
| `PROGRESS_UPDATE_INTERVAL_SECONDS` | `0.5` |
| `YTDLP_JS_RUNTIME` | `node` |
| `YTDLP_JS_RUNTIME_PATH` | unset |
| `YTDLP_COOKIES_FILE` | unset |
| `YTDLP_COOKIES_FROM_BROWSER` | unset |

## Optional cookies

Some public pages on Instagram, Facebook or other platforms may still require an
authenticated browser context depending on rate limits, age gates or regional rollout.
MediaForgeTool supports instance-level cookies only. Users cannot upload cookies through
the web UI.

Preferred deployment mode:

```env
YTDLP_COOKIES_FILE=secrets/cookies.txt
```

The file must use the Netscape cookies format accepted by `yt-dlp`. In Docker Compose,
`./secrets` is mounted read-only into the container and ignored by Git.

For local development, cookies can also be loaded from a browser profile on the same
machine:

```env
YTDLP_COOKIES_FROM_BROWSER=firefox:default
```

Use only one cookies source. When `YTDLP_COOKIES_FILE` is set, it takes precedence.
Treat cookies as credentials: keep `secrets/` private, avoid committing it, and rotate
the exported file when access changes.

Cookies are instance-level operational credentials. MediaForgeTool does not provide a web
flow for users to upload cookies, and enabling cookies on a public instance should be
treated as a deliberate deployment decision.

## Security notes

MediaForgeTool accepts public HTTP(S) URLs only and rejects obvious private, loopback and
link-local destinations before calling `yt-dlp`. That is a baseline SSRF guard, not a
full network sandbox for an Internet-facing service.

Cookies, when configured, are process-wide instance credentials. Do not enable them on
a public instance unless that operational risk is acceptable.

Keep concurrency and volume quotas conservative. Update `yt-dlp` regularly because
extractors track external platform changes.

YouTube extraction needs a JavaScript runtime for current `yt-dlp` challenge handling.
MediaForgeTool enables `node` by default for `yt-dlp`; set `YTDLP_JS_RUNTIME_PATH` if the
runtime is not discoverable from `PATH`.

Job creation has a simple in-process client-address rate limit for the single-instance
MVP. For a public deployment behind a reverse proxy, align proxy client-IP handling and
edge rate limits with that policy.

Retention, size, duration, concurrency and queue settings are process-local controls.
Keep `MAX_CONCURRENT_JOBS`, `MAX_QUEUE_SIZE`, `MAX_OUTPUT_SIZE_MB`,
`MAX_MEDIA_DURATION_SECONDS`, `OUTPUT_RETENTION_HOURS` and `TEMP_RETENTION_HOURS`
conservative for the host running the instance.

## Media Studio limits

The Studio is a lightweight self-hosted tool, not a full non-linear editor. Fast cuts and
splits use stream copy, so boundaries may align to nearby keyframes depending on the
source. Replacing audio keeps the video stream when possible and encodes the new audio as
AAC. Extracting or concatenating audio outputs MP3 or M4A.

Video concatenation intentionally uses the fast `-c copy` path. If videos differ in codec,
resolution, audio codec or container metadata, MediaForgeTool rejects the job with
`MEDIA_EDIT_INCOMPATIBLE_INPUTS` instead of guessing a re-encode profile. Users are
responsible for ensuring they have the right to transform and keep the media they process.

## Tests

```bash
uv run pytest
uv run ruff check .
```

Tests mock the platform boundary rather than downloading from public services.
