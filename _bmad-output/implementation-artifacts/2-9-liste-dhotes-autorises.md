# Story 2.9: Liste d'hotes autorises

Status: done

## Story

En tant que mainteneur,
je veux pouvoir limiter les Host headers acceptes par l'application,
afin de reduire les risques de routage ou de cache lies a des hosts inattendus en deploiement public.

## Acceptance Criteria

1. Une configuration `ALLOWED_HOSTS` existe avec default permissif pour le developpement local.
2. Les deploiements peuvent fournir une liste separee par virgules.
3. Les requetes avec Host autorise atteignent l'application.
4. Les requetes avec Host inattendu sont rejetees.
5. Le README documente le comportement et un exemple de configuration.
6. Les controles qualite passent.

## Tasks / Subtasks

- [x] Ajouter `ALLOWED_HOSTS` aux settings et `.env.example` (AC: 1, 2)
- [x] Ajouter `TrustedHostMiddleware` (AC: 3, 4)
- [x] Ajouter des tests Host autorise/refuse et parsing virgule (AC: 2, 3, 4)
- [x] Documenter `ALLOWED_HOSTS` dans le README (AC: 5)
- [x] Ajouter la story au planning et au suivi sprint (AC: 6)
- [x] Executer les controles qualite (AC: 6)

## Dev Notes

- Le default `*` preserve les tests, le dev local et les deploiements non configures.
- En production, `ALLOWED_HOSTS` devrait inclure le domaine public et les hosts internes necessaires au reverse proxy.
- Ce garde-fou ne remplace pas la configuration du reverse proxy.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `XDG_CACHE_HOME=/tmp/mediaforgetool-uv-cache rtk uv run ruff check .` -> all checks passed
- `rtk .venv/bin/python -m pytest tests/test_trusted_hosts.py -q` -> 3 passed, 1 pytest-asyncio deprecation warning under Python 3.14
- `rtk .venv/bin/python -m pytest -q` -> 56 passed, 1 pytest-asyncio deprecation warning under Python 3.14

### Completion Notes List

- Ajout de `ALLOWED_HOSTS` avec parsing comma-separated.
- Ajout de `TrustedHostMiddleware`.
- Ajout de tests pour host autorise, host refuse et parsing.
- README mis a jour avec l'exemple de configuration.

### File List

- `app/core/config.py`
- `app/main.py`
- `.env.example`
- `tests/test_trusted_hosts.py`
- `README.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/2-9-liste-dhotes-autorises.md`

## Change Log

- 2026-06-02: Story 2.9 creee, implementee et terminee.
