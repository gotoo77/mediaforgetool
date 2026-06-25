# Story 3.1: Contrats publics de gestion des jobs et extraits

Status: done

## Story

En tant que mainteneur,
je veux que les capacites de pause, reprise, suppression, bitrate MP3 et extraits soient documentees dans le contrat public,
afin que l'interface, l'API et les artefacts BMAD decrivent le meme produit exploitable.

## Acceptance Criteria

1. Le planning contient une Epic 3 dediee au controle local des traitements et extraits.
2. Le README ne presente plus les lots de segments comme hors scope.
3. Le README documente les options publiques `audio_bitrate_kbps`, `segment_start_seconds` et `segment_end_seconds`.
4. Le README documente les endpoints de pause, reprise, suppression unitaire et purge de l'historique inactif.
5. Les tests existants couvrant ces contrats passent.
6. Les controles qualite passent.

## Tasks / Subtasks

- [x] Ajouter l'Epic 3 et la Story 3.1 au planning (AC: 1)
- [x] Corriger le scope public du README sur les lots de segments (AC: 2)
- [x] Documenter les options de bitrate MP3 et d'extraits (AC: 3)
- [x] Documenter les endpoints de cycle de vie et nettoyage des jobs (AC: 4)
- [x] Ajouter la story au suivi sprint (AC: 5, 6)
- [x] Executer les controles qualite (AC: 5, 6)

## Dev Notes

- Les endpoints et champs documentes existaient deja dans `app/api/routes/jobs.py` et `app/schemas/job.py`.
- Les lots de segments restent des jobs independants crees par le navigateur; il ne s'agit pas d'une queue distribuee ni d'un traitement playlist.
- La suppression ignore les jobs actifs pour la purge globale et refuse la suppression directe d'un job actif.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run ruff check .` -> all checks passed
- `rtk uv run pytest -q` -> 61 passed, 1 pytest-asyncio deprecation warning under Python 3.14

### Completion Notes List

- Ajout de l'Epic 3 dans le planning BMAD.
- Documentation README alignee avec les options MP3, extraits, suggestions de segments et lots navigateur.
- Documentation README ajoutee pour pause, reprise, suppression d'un job et purge de l'historique inactif.

### File List

- `README.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/3-1-contrats-publics-de-gestion-des-jobs-et-extraits.md`

## Change Log

- 2026-06-06: Story 3.1 creee, implementee et terminee.
