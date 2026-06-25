# Story 2.2: Image Docker autonome et runbook minimal

Status: done

## Story

En tant que mainteneur,
je veux que l'image Docker embarque son propre healthcheck et que le README documente un lancement `docker run`,
afin de disposer d'un chemin de deploiement minimal meme sans Compose.

## Acceptance Criteria

1. Le Dockerfile declare un `HEALTHCHECK` qui cible `/healthz` sur le port applicatif configure.
2. Le healthcheck n'ajoute pas de dependance systeme supplementaire.
3. Le README documente un lancement `docker run` avec volumes persistants pour `storage`, `temp` et `secrets`.
4. Les controles `rtk uv run ruff check .` et `rtk uv run pytest -q` passent.

## Tasks / Subtasks

- [x] Ajouter un `HEALTHCHECK` Dockerfile base sur `urllib.request` (AC: 1, 2)
- [x] Documenter le build et le run Docker sans Compose (AC: 3)
- [x] Conserver le modele de stockage hors image pour les sorties, temporaires et cookies (AC: 3)
- [x] Executer les controles qualite (AC: 4)

## Dev Notes

- Le Dockerfile contient deja Python, `ffmpeg`, `nodejs` et l'application.
- Le healthcheck image et le healthcheck Compose ciblent la meme route `/healthz`.
- Compose peut surcharger le healthcheck image; le Dockerfile couvre surtout les usages `docker run`.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run ruff check .` -> all checks passed
- `rtk uv run pytest -q` -> 40 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk docker-compose config` -> compose config rendered successfully
- `rtk docker build -t mediaforgetool:codex-check .` -> image built successfully

### Completion Notes List

- Ajout d'un `HEALTHCHECK` dans le Dockerfile sans installation de `curl` ou `wget`.
- Documentation d'un runbook Docker minimal avec volumes persistants.
- Story 2.2 ajoutee au planning et marquee done.

### File List

- `Dockerfile`
- `README.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/2-2-image-docker-autonome-et-runbook-minimal.md`

## Change Log

- 2026-06-01: Story 2.2 creee, implementee et terminee.
