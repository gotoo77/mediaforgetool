# Phase 0 architecture record

## Constraints

- FastAPI monolith for the MVP
- SQLite and local files
- `yt-dlp` owns extractor behavior
- `ffmpeg` owns merge, remux and audio conversion work
- no distributed queue in Phase 1

## Flow

1. Validate and persist a media job.
2. Enqueue the job identifier in a bounded in-process runner.
3. Extract metadata and download into `temp/jobs/<job_id>`.
4. Publish the final MP3 or MP4 into `storage/jobs/<job_id>`.
5. Poll job status from the UI and serve the final file when completed.
6. Remove temporary files and expire retained outputs.

The job runner boundary is intentional. A future queue adapter can replace the internal
queue without moving `yt-dlp` concerns into HTTP routes.

## Proposed extensions

- [Playlist Import & Media Resolution](architecture/playlist_import_architecture.md):
  architecture cible pour importer des listes musicales, normaliser des pistes,
  rechercher des candidats media et reutiliser la queue de telechargement existante.
