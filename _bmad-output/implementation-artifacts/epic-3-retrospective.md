# Epic 3 Retrospective: Controle local des traitements et extraits

Status: done

## Summary

Epic 3 aligne le contrat public de MediaForgeTool avec les capacites deja exposees et
fiabilise le cycle de vie des jobs reprenables. La pause est maintenant respectee
avant le demarrage du worker comme pendant la phase de traitement, les sorties ne
sont pas publiees apres une pause tardive, et les jobs pauses ainsi que leurs
temporaires sont proteges contre les nettoyages automatiques ou manuels.

Les cinq stories de l'epic sont terminees:

- Story 3.1: Contrats publics de gestion des jobs et extraits
- Story 3.2: Pause fiable avant demarrage worker
- Story 3.3: Pause coherente pendant la phase de traitement
- Story 3.4: Protection des jobs pauses contre la purge
- Story 3.5: Conservation des temporaires reprenables

## Verification

- `rtk uv run pytest -q` -> 66 passed, 1 warning pytest-asyncio sous Python 3.14
- `rtk uv run ruff check .` -> passed

## What Worked

- Les regressions de concurrence ont ete traitees aux frontieres du runner: prise
  d'un job en file, retour du downloader et publication du fichier final.
- Le statut persiste en base reste la source de verite pour decider si un travail
  peut demarrer, continuer ou publier sa sortie.
- Les contrats API, les actions de l'interface et la documentation de pause,
  reprise, suppression, bitrate MP3 et extraits sont maintenant alignes.
- La notion de job reprenable est appliquee de facon coherente a la suppression de
  l'historique et au nettoyage des dossiers temporaires.
- Les tests cibles du runner, de l'API et du cleanup ont permis de couvrir chaque
  transition sans dependre d'un telechargement media reel.

## Risks Carried Forward

- La pause reste cooperative: elle est observee aux points de controle du runner,
  mais ne suspend pas instantanement un processus externe `yt-dlp` ou `ffmpeg`.
- La queue en memoire et le modele mono-processus limitent la reprise apres
  redemarrage et interdisent toujours un deploiement fiable avec plusieurs workers.
- Les temporaires reprenables peuvent occuper durablement du disque si des jobs
  pauses ou interrompus ne sont jamais repris ni geres explicitement.
- Les transitions de statut sont distribuees entre l'API, le runner et le cleanup;
  toute nouvelle phase devra reutiliser les memes ensembles de statuts proteges.
- Le warning `pytest-asyncio` sous Python 3.14 devra etre traite avant la suppression
  de `asyncio.get_event_loop_policy` annoncee pour Python 3.16.

## Suggested Next Epic Candidates

- Reprise apres redemarrage: recharger les jobs interrompus, reconstruire la queue
  et rendre explicite la politique de reprise automatique ou manuelle.
- Politique de retention: quotas disque, age maximal des jobs reprenables et
  controles utilisateur pour abandonner puis supprimer un job pause.
- Fiabilite du pipeline: annulation cooperative du sous-processus, timeouts par
  phase et erreurs plus actionnables pour `yt-dlp` et `ffmpeg`.
- Observabilite du cycle de vie: journal des transitions, durees par phase et
  metriques de queue, d'echec et d'espace disque.

## Change Log

- 2026-06-25: Retrospective Epic 3 creee et Epic 3 marque done.
