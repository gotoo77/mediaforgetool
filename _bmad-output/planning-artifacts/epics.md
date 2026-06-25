# Epics et stories - MVP MediaForgeTool

Source: `README.md`, `docs/architecture.md`.

## Epic 1: Downloader self-hosted MVP

Objectif: disposer d'une application FastAPI locale permettant d'inspecter, telecharger et convertir des medias publics en MP4 ou MP3 avec suivi de progression et retention controlee.

### Story 1.1: Socle FastAPI, jobs et telechargement media MVP

En tant qu'utilisateur self-hosted, je veux soumettre une URL publique, choisir MP4 ou MP3, suivre le traitement et recuperer le fichier final afin de telecharger un media sans compte utilisateur.

### Story 1.2: Durcissement exploitation et parcours public

En tant que mainteneur, je veux valider le parcours sur des medias reels, documenter les limites operationnelles et durcir les cas plateforme courants afin de rendre l'instance plus fiable hors environnement de test.

## Epic 2: Exploitation et packaging public

Objectif: renforcer les chemins de deploiement self-hosted afin qu'une instance MediaForgeTool soit plus observable, verifiable et exploitable hors poste de developpement.

### Story 2.1: Healthcheck Docker Compose leger

En tant que mainteneur,
je veux que le healthcheck Docker Compose utilise la route process-level `/healthz`,
afin de verifier l'etat du conteneur sans charger la page applicative ni declencher de travail media.

### Story 2.2: Image Docker autonome et runbook minimal

En tant que mainteneur,
je veux que l'image Docker embarque son propre healthcheck et que le README documente un lancement `docker run`,
afin de disposer d'un chemin de deploiement minimal meme sans Compose.

### Story 2.3: Image Docker sans donnees runtime

En tant que mainteneur,
je veux que l'image Docker ne copie pas les bases, sorties, temporaires ou secrets locaux,
afin de produire une image reproductible et sans donnees d'exploitation accidentelles.

### Story 2.4: Sauvegarde et restauration du stockage local

En tant que mainteneur,
je veux disposer d'un script documente pour sauvegarder et restaurer SQLite et les sorties retenues,
afin de pouvoir deplacer ou recuperer une instance self-hosted sans manipulations manuelles fragiles.

### Story 2.5: Logs JSON documentes et testes

En tant que mainteneur,
je veux que le format de logs JSON soit teste et documente,
afin de pouvoir brancher l'application sur des outils d'exploitation sans deviner les champs disponibles.

### Story 2.6: Headers HTTP de durcissement navigateur

En tant que mainteneur,
je veux que l'application ajoute des headers HTTP de securite de base sur les pages et l'API,
afin de reduire les risques navigateur courants lors d'une exposition derriere reverse proxy.

### Story 2.7: Limite de taille des corps HTTP

En tant que mainteneur,
je veux que l'application rejette les corps HTTP trop volumineux avant traitement metier,
afin de reduire la surface d'abus de l'API JSON self-hosted.

### Story 2.8: Correlation request id

En tant que mainteneur,
je veux que chaque reponse expose un `X-Request-ID` et que les logs JSON puissent porter ce meme identifiant,
afin de correler plus facilement les incidents entre reverse proxy, application et logs.

### Story 2.9: Liste d'hotes autorises

En tant que mainteneur,
je veux pouvoir limiter les Host headers acceptes par l'application,
afin de reduire les risques de routage ou de cache lies a des hosts inattendus en deploiement public.

## Epic 3: Controle local des traitements et extraits

Objectif: rendre explicites, verificables et exploitables les controles locaux autour du cycle de vie des jobs, des extraits media et des lots de segments crees depuis le navigateur.

### Story 3.1: Contrats publics de gestion des jobs et extraits

En tant que mainteneur,
je veux que les capacites de pause, reprise, suppression, bitrate MP3 et extraits soient documentees dans le contrat public,
afin que l'interface, l'API et les artefacts BMAD decrivent le meme produit exploitable.

### Story 3.2: Pause fiable avant demarrage worker

En tant qu'utilisateur,
je veux qu'un job mis en pause pendant qu'il est encore en file d'attente ne demarre pas ensuite automatiquement,
afin que l'action Pause soit respectee meme avant que le worker commence le telechargement.

### Story 3.3: Pause coherente pendant la phase de traitement

En tant qu'utilisateur,
je veux que l'action Pause reste acceptee quand un job est en phase `processing`,
afin que les controles affiches dans l'interface correspondent au contrat API et que le fichier final ne soit pas publie apres une pause tardive.

### Story 3.4: Protection des jobs pauses contre la purge

En tant qu'utilisateur,
je veux qu'un job mis en pause ne soit pas supprime par les controles de nettoyage d'historique,
afin de pouvoir reprendre volontairement un traitement suspendu sans le perdre par erreur.

### Story 3.5: Conservation des temporaires reprenables

En tant qu'utilisateur,
je veux que le nettoyage automatique conserve les dossiers temporaires des jobs pauses ou interrompus,
afin qu'une reprise volontaire ne perde pas les donnees partielles encore utiles.
