# Story 2.3: Image Docker sans donnees runtime

Status: done

## Story

En tant que mainteneur,
je veux que l'image Docker ne copie pas les bases, sorties, temporaires ou secrets locaux,
afin de produire une image reproductible et sans donnees d'exploitation accidentelles.

## Acceptance Criteria

1. Le Dockerfile ne copie plus les repertoires runtime `storage` et `temp` depuis le workspace.
2. L'image conserve des repertoires runtime vides utilisables par defaut.
3. `.dockerignore` exclut les contenus runtime et secrets du contexte de build.
4. Le README documente que les donnees locales restent hors image.
5. Les controles `rtk uv run ruff check .`, `rtk uv run pytest -q`, `rtk docker-compose config` et un build Docker passent.

## Tasks / Subtasks

- [x] Remplacer `COPY storage` et `COPY temp` par la creation de dossiers vides dans le Dockerfile (AC: 1, 2)
- [x] Exclure `storage/` et `temp/` du contexte Docker (AC: 3)
- [x] Conserver l'exclusion des secrets locaux (AC: 3)
- [x] Documenter le comportement dans le README (AC: 4)
- [x] Executer les controles qualite et packaging (AC: 5)

## Dev Notes

- `StorageService.prepare_directories()` cree deja `storage/jobs` et `temp/jobs` au demarrage.
- Le `RUN mkdir -p storage/jobs temp/jobs` garde un comportement lisible pour l'image meme sans volumes montes.
- Les volumes Compose et `docker run` restent le chemin recommande pour conserver SQLite, sorties et temporaires hors image.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run ruff check .` -> all checks passed
- `rtk uv run pytest -q` -> 40 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk docker-compose config` -> compose config rendered successfully
- `rtk docker build -t mediaforgetool:codex-check .` -> image built successfully with `RUN mkdir -p storage/jobs temp/jobs`

### Completion Notes List

- Suppression de la copie des dossiers `storage` et `temp` dans l'image.
- Exclusion complete de `storage/` et `temp/` du contexte Docker.
- Documentation README ajoutee sur les donnees runtime hors image.

### File List

- `Dockerfile`
- `.dockerignore`
- `README.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/2-3-image-docker-sans-donnees-runtime.md`

## Change Log

- 2026-06-01: Story 2.3 creee, implementee et terminee.
