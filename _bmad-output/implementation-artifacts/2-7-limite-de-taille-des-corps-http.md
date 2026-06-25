# Story 2.7: Limite de taille des corps HTTP

Status: done

## Story

En tant que mainteneur,
je veux que l'application rejette les corps HTTP trop volumineux avant traitement metier,
afin de reduire la surface d'abus de l'API JSON self-hosted.

## Acceptance Criteria

1. Une limite configurable `MAX_REQUEST_BODY_BYTES` existe avec un default compatible avec les petits payloads JSON de MediaForgeTool.
2. Les requetes dont `Content-Length` depasse la limite sont rejetees en `413`.
3. La reponse d'erreur contient un contrat structure `REQUEST_BODY_TOO_LARGE`.
4. Les petites requetes continuent d'atteindre les routes API.
5. Le README documente la limite et rappelle qu'elle ne remplace pas les limites reverse proxy.
6. Les tests couvrent rejet et passage route.
7. Les controles qualite passent.

## Tasks / Subtasks

- [x] Ajouter la configuration `MAX_REQUEST_BODY_BYTES` (AC: 1)
- [x] Ajouter un middleware de rejet par `Content-Length` (AC: 2, 3, 4)
- [x] Ajouter des tests API de limite de corps (AC: 6)
- [x] Documenter la limite dans README et `.env.example` (AC: 5)
- [x] Ajouter la story au planning et au suivi sprint (AC: 7)
- [x] Executer les controles qualite (AC: 7)

## Dev Notes

- La limite s'applique a la surface HTTP applicative et aux payloads JSON attendus.
- Le middleware utilise `Content-Length` pour eviter de consommer le body avant FastAPI.
- Un deploiement public doit encore configurer des limites de taille et de connexion au reverse proxy.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `XDG_CACHE_HOME=/tmp/mediaforgetool-uv-cache rtk uv run ruff check .` -> all checks passed
- `rtk .venv/bin/python -m pytest tests/test_request_limits.py -q` -> 2 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk .venv/bin/python -m pytest -q` -> 49 passed, 1 pytest-asyncio deprecation warning under Python 3.14

### Completion Notes List

- Ajout de `MAX_REQUEST_BODY_BYTES` avec default 1 MiB.
- Ajout d'un middleware de rejet `413` base sur `Content-Length`.
- Ajout de tests rejet/passage pour l'API.
- README et `.env.example` mis a jour.

### File List

- `app/core/config.py`
- `app/main.py`
- `.env.example`
- `tests/test_request_limits.py`
- `README.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/2-7-limite-de-taille-des-corps-http.md`

## Change Log

- 2026-06-02: Story 2.7 creee, implementee et terminee.
