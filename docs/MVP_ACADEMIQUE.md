# MVP académique — choix, RSE, handicap et limites

Source Markdown destinée à validation avant un éventuel rendu Word ou slides. État au 22 septembre 2026 ; voir [Discovery](DISCOVERY_DONNEES_KPI.md), [veille](VEILLE_TECHNO_REGLEMENTAIRE.md), [SWOT source](SWOT_SOURCE.md) et [roadmap](ROADMAP_ACADEMIQUE.md).

## Problème et décision produit

Une équipe de service client ou de supply chain doit lire des avis après achat, distinguer note et verbatim, puis décider quels irritants méritent une investigation. Le MVP démontre l'import ou la collecte dans les limites autorisées, la persistance, la classification de sentiment, la restitution, les exports et une boucle de correction humaine. La proposition de valeur porte sur une **aide à la priorisation**, pas sur une décision automatique ni sur la preuve d'une cause logistique.

Les quatre KPI de cadrage sont la note moyenne, la part d'avis négatifs, le taux de réponse visible lorsque son statut est fiable, et le volume d'avis analysés comme indicateur de couverture. Le rapport ne doit pas extrapoler des résultats d'un échantillon par étoiles ou d'une collecte interrompue. La tentative réelle Showroomprivé s'est arrêtée sur HTTP 403 : zéro avis extrait, donc pas de preuve de collecte exhaustive de plus de 10 000 avis.

## Choix et exclusions

| Décision | Justification et preuve | Limite |
| --- | --- | --- |
| Conserver import CSV/JSON et chaîne API–PostgreSQL–MLflow–frontend. | Parcours démontré par tests, CI et E2E ; modèle v53 évalué avec split propre. | La provenance et les droits sur chaque fichier importé doivent être établis ; l'import ne prouve pas un scraping. |
| Garder contrôle humain des avis, thèmes et décisions. | Sentiment et thèmes sont imparfaits ; les exemples et corrections permettent un examen métier. | La qualité des corrections dépend du contexte et des personnes qui les produisent. |
| Ne pas développer une nouvelle intégration source ou un modèle plus complexe avant soutenance. | Aucune preuve que cela comblerait légalement le besoin de collecte ou améliorerait honnêtement la valeur métier. | Le périmètre de sources reste limité. |
| Ne pas promettre un SaaS de production durci. | La VM scolaire et la supervision servent la démonstration technique. | Sécurité, accessibilité et gouvernance des données demandent encore une validation professionnelle. |

## Parties prenantes et ressources

Profils envisagés : responsable service client, responsable supply chain, responsable expérience client, analyste data, direction ; aucun entretien réalisé. L'équipe projet utilise le dépôt Git, Python/scikit-learn, PostgreSQL, MLflow, FastAPI, React, Celery/Redis, Docker Compose, GitHub Actions et la VM scolaire déjà mise à disposition. Aucun abonnement nouveau n'est requis pour les livrables documentaires ; le temps humain et le coût alloué de la VM ne sont pas chiffrés. La [roadmap](ROADMAP_ACADEMIQUE.md) détaille jalons, validation et maintenance.

## Handicap et accessibilité — engagement réaliste

Pour la démonstration, vérifier manuellement au moins la navigation clavier du chemin connexion → lancement/import → rapport, les libellés des contrôles, la lisibilité des états et erreurs, et les contrastes des indicateurs essentiels. Prévoir une alternative textuelle aux graphiques ou couleurs quand la donnée est utilisée pour décider. Les critères [WCAG 2.2](https://www.w3.org/TR/WCAG22/) servent de guide de test. **Aucun audit complet ni conformité WCAG/RGAA n'est revendiqué** ; l'obligation RGAA dépend du champ d'application de l'organisme et du service.

## RSE et protection des personnes

Social : éviter qu'un sentiment automatique serve seul à juger un client ou un salarié ; lire des verbatims en contexte, reconnaître les biais de collecte et conserver une possibilité de correction. Données : limiter les champs personnels utilisés, contrôler l'accès par rôles, définir une durée de conservation avant tout usage réel et examiner les droits sur la source. Environnement : une meilleure lecture des irritants de livraison **pourrait** aider à cibler des corrections évitant des reprises inutiles ; aucun gain de transport, énergie ou carbone n'a été mesuré. Éviter les entraînements répétés sans question d'évaluation précise est un choix de sobriété du MVP, non un bilan chiffré.

## SWOT et réglementation dans l'arbitrage

La [SWOT](SWOT_SOURCE.md) conserve comme faiblesse la collecte >10 000 non démontrée, et comme menace l'accès aux données et le cadre légal. La [veille](VEILLE_TECHNO_REGLEMENTAIRE.md) distingue obligation juridique, recommandation et pratique volontaire : présence possible de données personnelles dans les avis, restrictions contractuelles de plateformes, durée de conservation à définir, qualification AI Act et RGAA à examiner selon l'usage réel. Ces points bornent la démonstration ; ils ne déclenchent aucune nouvelle fonctionnalité dans ce chantier.
