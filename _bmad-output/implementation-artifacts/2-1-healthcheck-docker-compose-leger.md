# Story 2.1: Healthcheck Docker Compose leger

Status: done

## Story

En tant que mainteneur,
je veux que le healthcheck Docker Compose utilise la route process-level `/healthz`,
afin de verifier l'etat du conteneur sans charger la page applicative ni declencher de travail media.

## Acceptance Criteria

1. Le healthcheck Compose cible `GET /healthz` sur le port applicatif configure.
2. Le probe reste autonome dans l'image existante, sans ajouter de dependance systeme.
3. Le README documente comment inspecter le statut du conteneur.
4. Les controles `rtk uv run ruff check .` et `rtk uv run pytest -q` passent.

## Tasks / Subtasks

- [x] Remplacer le probe Compose `/` par `/healthz` (AC: 1, 2)
- [x] Conserver l'utilisation de Python standard library pour eviter `curl`/`wget` dans l'image (AC: 2)
- [x] Documenter `docker compose ps` dans la section Docker du README (AC: 3)
- [x] Executer les controles qualite (AC: 4)

## Dev Notes

- La route `/healthz` a ete livree dans Story 1.2 pour un probe process-level leger.
- Le conteneur contient deja Python; `urllib.request` suffit au healthcheck Compose.
- Le probe ne doit pas appeler `/api/jobs`, ni inspecter une URL, ni creer de job.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run ruff check .` -> all checks passed
- `rtk uv run pytest -q` -> 40 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk docker-compose config` -> compose config rendered successfully with `/healthz` healthcheck

### Completion Notes List

- Healthcheck Compose modifie pour appeler `/healthz` avec timeout explicite.
- Documentation Docker mise a jour avec `docker compose ps`.
- Epic 2 ajoute au planning comme suite exploitation/packaging.

### File List

- `docker-compose.yml`
- `README.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/2-1-healthcheck-docker-compose-leger.md`

## Change Log

- 2026-06-01: Story 2.1 creee, implementee et terminee.
