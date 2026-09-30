# Roadmap académique — jalons vérifiables et préparation de la soutenance

Source Markdown. Jalons documentés le 22 septembre 2026 ; scénario de ressources ajouté le 30 septembre 2026. **La date de soutenance n'a pas été communiquée** : les périodes « avant soutenance » sont relatives et ne prétendent pas fixer un calendrier officiel. Les dates passées ci-dessous correspondent aux preuves connues ; elles ne réécrivent pas l'historique du projet.

## Jalons et livrables

| Période défendable | Jalon et livrable | Ressources humaines, techniques et monétaires | Indicateur de validation / test | Maintenance ou suite |
| --- | --- | --- | --- | --- |
| Jusqu'au 21/09/2026, état déjà obtenu | Protocole ML propre, modèle v53 évalué puis promu ; migrations jusqu'à `20260921_0008`. | Équipe projet ; corpus disponible, scikit-learn, MLflow, PostgreSQL. Valorisation pédagogique détaillée ci-dessous, distincte des dépenses réelles. | Tests ML/migrations et métriques du run à relier aux captures du registre. | Conserver v52 comme possibilité de retour applicatif ; vérifier la cohérence des versions et données avant changement. |
| 22/09/2026, démontré | CI, deux déploiements automatisés sur VM scolaire, rollback manuel entre deux SHA dont un commit vide ; contrôle manuel de supervision sain. | Équipe projet ; GitHub Actions, Ansible et Docker Compose. VM scolaire déjà mise à disposition par la formation ; coût alloué et dépense cash réelle non documentés. | Runs CI/déploiement/monitoring et KPI DevOps archivés dans [DEVOPS_EVIDENCE.md](DEVOPS_EVIDENCE.md). | Surveiller disponibilité et disque ; suivre les procédures du runbook, sans purge des ressources scolaires. |
| Depuis le 22/09/2026, preuve acquise | Scheduler GitHub : heartbeat `schedule` réussi, événement Monitor créé puis job `skipped`. | GitHub Actions déjà utilisé pour les workflows ; aucun prix, quota ou montant facturé n'est déduit de cette utilisation. | [Heartbeat 35765192366](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35765192366) et [Monitor 35764642522](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35764642522). | Une sonde **planifiée active** de la VM reste à démontrer séparément ; ne pas présenter l'événement ignoré comme une sonde. |
| Prochaine revue documentaire, **avant la soutenance** | Discovery, quatre KPI, veille sourcée, MVP/RSE/handicap, SWOT validée puis slide unique, dossier collecte, preuves MLflow et scénario de démo cohérent. | Équipe projet et, si disponible, relecteur métier ; dépôt et sources officielles. Valorisation illustrative de la documentation ci-dessous. | Contrôle ligne par ligne contre le PDF normatif ; liens valides ; formats finaux validés ; quatre KPI avec formule/source/période/limite ; aucune preuve inventée. | Mettre à jour dates de consultation, liens et statut des preuves si l'état change. |
| Répétition finale, **après validation des documents et avant la soutenance** | Démonstration chronométrée, fichiers finaux et captures de repli. | Équipe projet ; environnement scolaire existant ou captures archivées si VM indisponible. Valorisation illustrative ci-dessous. | Vérifier ouverture des rendus, parcours démo, distinction cold start v1/registre conservé v53 et exposé honnête des limites. | Plan de repli documentaire si la VM ou une source externe ne répond pas. |

## Suivi, tests et maintenance

- **Suivi métier :** quatre KPI du document [Discovery](DISCOVERY_DONNEES_KPI.md), toujours accompagnés de l'effectif, de la source, de la période et de la représentativité. Ne fixer aucun objectif numérique sans base métier observée.
- **Suivi technique :** CI backend/frontend/build, E2E existant, Deployment Cycle Time/Frequency/Success Rate, état du monitoring et de ses alertes. Un run `schedule` créé peut rester `skipped` ; seule une sonde active prouve la supervision planifiée de la VM.
- **Tests avant présentation :** relire les assertions documentaires, vérifier les liens de runs, les exports finaux et l'accessibilité élémentaire du parcours de démonstration. Aucun réentraînement ou nouveau déploiement n'est requis par cette roadmap documentaire.
- **Maintenance préventive :** contrôle des accès/conditions des sources, renouvellement de la veille réglementaire, lecture des alertes, contrôle des sauvegardes et de la provenance des datasets.
- **Maintenance curative :** suivre le runbook en cas d'échec, diagnostiquer avant tout restart ; rollback applicatif limité au code et aux images, sans downgrade DB démontré.

## Ressources et coûts — scénario pédagogique

Le projet utilise une **machine personnelle existante** pour le développement et une **VM scolaire fournie** pour les déploiements de démonstration. GitHub et GitHub Actions hébergent le dépôt et exécutent les workflows. Docker, PostgreSQL, Redis, MLflow, FastAPI, React, scikit-learn et Ansible sont les outils effectivement employés ; leur disponibilité ou leur licence open source ne signifie pas que le travail et l'exploitation ont un coût économique nul. Aucun relevé exhaustif des dépenses engagées n'est disponible : **la dépense cash réelle totale n'est pas déterminable à partir des pièces du projet**.

Le tableau suivant est une **valorisation illustrative**, sans valeur de feuille de temps ou de facture. Il suppose 36 jours-personne répartis par phase et un tarif journalier moyen (TJM) indicatif de 350 € par jour-personne. Les 36 jours ne sont **pas** un relevé du temps réellement passé ; 350 € est une hypothèse pédagogique, non un tarif contractuel.

| Étape | Ressource humaine | Ressources techniques internes / externes | Coût réel connu | Valorisation humaine estimée | Hypothèse |
| --- | --- | --- | --- | ---: | --- |
| Discovery, cadrage et veille | Équipe projet, relecture métier éventuelle | Machine personnelle, dépôt GitHub, sources documentaires | Non déterminé | 1 050 € | 3 j × 350 € |
| Collecte et contrôle des données | Équipe projet | Machine personnelle, Chrome/Playwright, stockage privé | Non déterminé | 2 800 € | 8 j × 350 € |
| Application, PostgreSQL et ETL | Équipe projet | Machine personnelle, PostgreSQL, Redis, FastAPI, React, Docker | Non déterminé | 3 500 € | 10 j × 350 € |
| ML et évaluation | Équipe projet | scikit-learn, MLflow, corpus d'entraînement | Non déterminé | 2 450 € | 7 j × 350 € |
| CI, déploiement et supervision | Équipe projet | GitHub Actions, Ansible, Docker Compose, VM scolaire fournie | Non déterminé | 1 750 € | 5 j × 350 € |
| Documentation et soutenance | Équipe projet, relecteur éventuel | Dépôt, outils de rendu, environnement de démonstration | Non déterminé | 1 050 € | 3 j × 350 € |
| **Total illustratif** | **36 jours-personne supposés** | **Ressources existantes ou fournies** | **Non déterminable** | **12 600 €** | **36 j × 350 €** |

Les **12 600 € ne sont pas une dépense réellement engagée**. Pour une éventuelle mise en production, une enveloppe **distincte et purement indicative** de 50 à 100 € HT par mois pour un petit hébergement avec sauvegarde peut servir de première hypothèse ; elle devra être recalculée selon le fournisseur, la capacité, les sauvegardes et les exigences de service. Ce n'est ni une facture ni un coût mesuré de la VM scolaire. La date officielle de soutenance et les disponibilités des intervenants restent à renseigner avant d'assigner des échéances calendaires.
