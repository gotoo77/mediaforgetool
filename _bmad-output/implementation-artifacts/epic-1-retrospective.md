# Epic 1 Retrospective: Downloader self-hosted MVP

Status: done

## Summary

Epic 1 livre le MVP MediaForgeTool attendu: interface web FastAPI/Jinja, inspection de source, creation de jobs MP3/MP4, suivi de progression, historique local, telechargement de sortie, persistence SQLite, runner en arriere-plan, nettoyage, limites operationnelles et documentation de verification.

Les deux stories de l'epic sont terminees:

- Story 1.1: Socle FastAPI, jobs et telechargement media MVP
- Story 1.2: Durcissement exploitation et parcours public

## Verification

- `rtk uv run ruff check .` -> passed
- `rtk uv run pytest -q` -> 40 passed, 1 warning pytest-asyncio sous Python 3.14

## What Worked

- Le modele mono-processus reste coherent avec le perimetre Phase 1 et evite une complexite de queue distribuee prematuree.
- Les tests mockent la frontiere plateforme, ce qui rend la suite rapide et stable sans dependance aux comportements courants de plateformes publiques.
- Les contrats d'erreur API les plus importants sont couverts: URL invalide, rate limit, queue pleine, job absent, sortie non prete et sortie expiree.
- La documentation de smoke test clarifie la difference entre verification applicative locale et validation reelle dependante de `yt-dlp`, `ffmpeg`, runtime JavaScript et cookies.

## Risks Carried Forward

- Le comportement en production dependra toujours des changements de plateformes publiques et de la version courante de `yt-dlp`.
- La garde SSRF applicative reste une protection MVP; une exposition Internet publique devrait ajouter une politique reseau/sandbox plus stricte.
- Le modele mono-processus doit rester documente: plusieurs workers Uvicorn creeraient plusieurs queues memoire.
- La route `/healthz` valide seulement la reponse du processus FastAPI, pas la disponibilite complete du pipeline media.

## Suggested Next Epic Candidates

- Hardening de deploiement public: sandbox reseau, headers, observabilite, logs structures exploitables, sauvegarde/restauration SQLite.
- Parcours utilisateur avance: pause/reprise exposee dans l'UI, meilleure gestion des segments, retentatives controlees, details d'erreur plus actionnables.
- Packaging exploitation: image Docker versionnee, healthcheck Compose, exemples systemd/reverse proxy, configuration cookies documentee par scenario.

## Change Log

- 2026-06-01: Retrospective Epic 1 creee et Epic 1 marque done.
