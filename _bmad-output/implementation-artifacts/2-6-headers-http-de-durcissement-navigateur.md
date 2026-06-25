# Story 2.6: Headers HTTP de durcissement navigateur

Status: done

## Story

En tant que mainteneur,
je veux que l'application ajoute des headers HTTP de securite de base sur les pages et l'API,
afin de reduire les risques navigateur courants lors d'une exposition derriere reverse proxy.

## Acceptance Criteria

1. Les pages HTML et les reponses API incluent des headers de durcissement navigateur.
2. La CSP autorise les assets same-origin et les thumbnails HTTPS/data sans autoriser l'embarquement d'objets ou le framing.
3. Les headers `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` et `Permissions-Policy` sont presents.
4. Les headers sont couverts par des tests.
5. Le README documente les headers et rappelle que TLS, limites reverse proxy et politique egress restent hors application.
6. Les controles qualite passent.

## Tasks / Subtasks

- [x] Ajouter un middleware FastAPI de headers HTTP (AC: 1, 2, 3)
- [x] Tester les headers sur une page et une route API (AC: 4)
- [x] Documenter le durcissement HTTP dans le README (AC: 5)
- [x] Ajouter la story au planning et au suivi sprint (AC: 6)
- [x] Executer les controles qualite (AC: 6)

## Dev Notes

- Le MVP n'ajoute pas de reverse proxy applicatif; ces headers sont des defaults au niveau FastAPI.
- La CSP garde `img-src https: data:` pour les thumbnails exposes par les plateformes publiques.
- Une exposition Internet publique doit encore traiter TLS, limites de taille, auth eventuelle et egress network policy hors de cette story.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `XDG_CACHE_HOME=/tmp/mediaforgetool-uv-cache rtk uv run ruff check .` -> all checks passed
- `rtk .venv/bin/python -m pytest tests/test_security_headers.py -q` -> 2 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk .venv/bin/python -m pytest -q` -> 47 passed, 1 pytest-asyncio deprecation warning under Python 3.14

### Completion Notes List

- Ajout d'un middleware FastAPI pour les headers de securite de base.
- Ajout de tests page/API pour verifier les headers.
- README mis a jour avec les headers et les limites hors application.

### File List

- `app/main.py`
- `tests/test_security_headers.py`
- `README.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/2-6-headers-http-de-durcissement-navigateur.md`

## Change Log

- 2026-06-02: Story 2.6 creee, implementee et terminee.
