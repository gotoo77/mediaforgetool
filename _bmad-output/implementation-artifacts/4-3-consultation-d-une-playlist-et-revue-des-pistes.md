# Story 4.3: Consultation d'une playlist et revue des pistes

Status: done

## Story

En tant qu'utilisateur,
je veux consulter une playlist importee et ses pistes normalisees,
afin de verifier le contenu avant toute recherche ou tout telechargement.

## Acceptance Criteria

1. L'API liste les imports recents et retourne le detail pagine d'une playlist.
2. L'UI propose un espace "Import de liste" distinct du formulaire URL existant.
3. Les pistes montrent au minimum artiste, titre, album si disponible et etat courant.
4. Les erreurs de ligne sont visibles sans exposer de trace interne.
5. L'historique et le formulaire de telechargement actuels restent fonctionnels.
6. Le rechargement de la page ne fait pas perdre l'import persiste.

## Tasks / Subtasks

- [x] Persister les erreurs de ligne d'import pour consultation apres rechargement
- [x] Ajouter `GET /api/playlists` avec pagination des imports recents
- [x] Ajouter `GET /api/playlists/{playlist_id}` avec pagination des pistes
- [x] Afficher un espace UI distinct pour l'import CSV Shazam
- [x] Afficher imports recents, pistes, et avertissements de parsing
- [x] Preserver le formulaire URL et l'historique existants
- [x] Ajouter les tests API et mettre a jour les garde-fous de domaine
- [x] Executer les controles qualite

## Dev Notes

- Les issues d'import sont conservees dans `playlist_import_issues`; le fichier source
  complet reste non persiste.
- La route detail pagine uniquement les pistes; les issues d'import sont renvoyees avec
  le detail de playlist pour garder les avertissements visibles.
- L'UI charge les imports recents au demarrage, ce qui restaure la revue apres reload.
- Aucun endpoint de piste separe n'est introduit; la surface publique reste sous
  `/api/playlists`.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_playlists_api.py -q` -> 9 passed
- `rtk uv run ruff check app tests/test_playlists_api.py` -> all checks passed
- `rtk node --check app/static/app.js` -> syntax OK
- `rtk uv run pytest -q` -> 97 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run ruff check .` -> all checks passed

### Completion Notes List

- Les imports recents sont listables via l'API et l'UI.
- Une playlist importee expose ses pistes paginees et ses avertissements persistants.
- Le formulaire URL et l'historique de telechargement existants restent separes.
- Le reload conserve l'import car l'UI relit les playlists depuis SQLite.

### File List

- `app/api/routes/playlists.py`
- `app/db/init_db.py`
- `app/models/__init__.py`
- `app/models/playlist.py`
- `app/schemas/playlist.py`
- `app/services/playlist_import/service.py`
- `app/static/app.css`
- `app/static/app.js`
- `app/templates/index.html`
- `tests/test_playlist_domain.py`
- `tests/test_playlists_api.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/4-3-consultation-d-une-playlist-et-revue-des-pistes.md`

## Change Log

- 2026-06-26: Story implementee et placee en review.
