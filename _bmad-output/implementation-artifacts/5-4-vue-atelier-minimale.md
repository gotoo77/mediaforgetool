# Story 5.4: Vue Atelier minimale

Status: review

## Story

En tant qu'utilisateur,
je veux une nouvelle vue `Atelier` claire et separee du telechargement,
afin de choisir une operation, selectionner mes sources, regler quelques options et suivre
le job cree.

## Acceptance Criteria

1. Une navigation permet d'acceder a `Telechargement` et `Atelier` sans perdre la page
   actuelle.
2. La vue Atelier affiche les assets disponibles avec type, nom, duree et origine quand
   connus.
3. L'utilisateur peut choisir les operations V1: remplacer audio, retirer audio, extraire
   audio, decouper en deux.
4. Chaque operation affiche seulement les champs utiles et des validations lisibles.
5. La creation de job, le polling et le telechargement de sortie fonctionnent depuis la
   vue.
6. L'interface reste dense, sobre et orientee outil; pas de landing page.
7. La page reste utilisable mobile et desktop sans chevauchement de textes.
8. Les textes visibles restent fonctionnels et ne documentent pas l'implementation.

## Tasks / Subtasks

- [x] Ajouter route/page Atelier cote FastAPI/Jinja (AC: 1)
- [x] Adapter la navigation existante (AC: 1)
- [x] Ajouter JS de chargement assets et selection d'operation (AC: 2-5)
- [x] Ajouter formulaires operationnels V1 (AC: 3, 4)
- [x] Ajouter polling de job atelier et liens de sortie (AC: 5)
- [x] Ajouter styles responsive (AC: 6, 7)
- [x] Ajouter tests minimaux routes/templates si existants (AC: 1)

## Dev Notes

- Ne pas faire une timeline professionnelle en V1.
- Preferer des panneaux compacts et des controles explicites:
  - select asset video/audio;
  - input timecode;
  - input offset;
  - boutons d'action.
- Les futures operations de concat devront s'inserer sans refonte majeure.

## Testing Requirements

- Tests route page Atelier 200.
- Tests JS manuels via navigateur local.
- Verification responsive desktop/mobile avant finalisation frontend.

## References

- `app/templates/index.html`
- `app/static/app.js`
- `app/static/app.css`
- `app/api/routes/pages.py`

## Definition of Done

- L'Atelier est accessible et utilisable pour les operations V1.
- Les erreurs utilisateur sont visibles.
- Les sorties sont telechargeables.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `rtk uv run pytest tests/test_media_edit.py -q`
- `rtk uv run pytest tests/test_jobs_api.py::test_home_versions_static_assets -q`
- `rtk uv run ruff check .`
- `rtk uv run pytest -q`

### Completion Notes List

- Ajout d'une vue `Atelier` separee de la vue telechargement avec navigation locale.
- Ajout du chargement des assets Studio, filtrage par operation, validations lisibles et lancement de jobs V1.
- Ajout d'un endpoint de telechargement par sortie pour les jobs multi-sorties comme `split_media`.
- Les operations de concatenation restent prevues pour la story 5.5.

### File List

- `app/api/routes/studio.py`
- `app/schemas/studio.py`
- `app/templates/index.html`
- `app/static/app.js`
- `app/static/app.css`
- `tests/test_jobs_api.py`
- `tests/test_media_edit.py`

## Change Log

- 2026-06-30: Story creee et placee en ready-for-dev.
- 2026-06-30: Vue Atelier minimale implementee et placee en review.
