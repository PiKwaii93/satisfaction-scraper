# Cadrage projet - Satisfaction Client

## 1. Contexte

Les avis clients sont une source directe d'information sur l'experience reelle apres achat. Ils permettent d'identifier des problemes de livraison, de qualite produit, de service client, de remboursement, de prix ou de conformite.

Dans beaucoup d'entreprises, ces avis sont lus manuellement ou analyses par echantillonnage. Cette approche est lente, difficile a reproduire et peut faire manquer des signaux faibles importants.

Le projet Satisfaction Client vise a transformer ces verbatims en indicateurs actionnables pour des equipes metier.

## 2. Problematique

Comment aider une entreprise a analyser rapidement un grand volume d'avis clients afin d'identifier les irritants prioritaires, suivre l'evolution de la satisfaction et ameliorer sa prise de decision ?

## 3. Proposition de valeur

| Axe | Reponse du projet |
| --- | --- |
| Why | Les verbatims contiennent une information riche mais difficile a exploiter manuellement. |
| What | Une application qui collecte ou importe des avis, predit le sentiment, detecte des irritants et produit un rapport metier. |
| Value | Les equipes peuvent prioriser les sujets critiques et suivre la qualite percue avec des donnees historisees. |

## 4. Public cible

| Persona | Besoin | Valeur attendue |
| --- | --- | --- |
| Responsable service client | Identifier les avis critiques et les sujets recurrents. | Reagir plus vite et mieux prioriser les reponses. |
| Responsable supply chain | Detecter les problemes de livraison, delais, conformite ou installation. | Corriger les irritants operationnels. |
| Responsable experience client | Comprendre les forces et faiblesses percues. | Suivre la satisfaction par entreprise ou periode. |
| Analyste data | Disposer d'une donnee propre, historisee et exportable. | Auditer le modele et enrichir le corpus. |
| Direction | Consulter une synthese claire. | Arbitrer les priorites d'amelioration. |

## 5. Besoins identifies

- Collecter des avis publics depuis Trustpilot.
- Importer des avis via CSV pour couvrir d'autres sources.
- Classer les verbatims en `Negatif`, `Neutre`, `Positif`.
- Ne pas se limiter a la note client.
- Identifier les irritants principaux.
- Afficher les avis critiques et les incoherences note / texte.
- Comparer plusieurs entreprises.
- Exporter les resultats.
- Corriger les erreurs de prediction.
- Reentrainer le modele avec les corrections humaines.

## 6. KPIs metier

Les **quatre KPI retenus pour la Discovery** sont définis avec formule, source,
période et règles de représentativité dans [docs/DISCOVERY_DONNEES_KPI.md](docs/DISCOVERY_DONNEES_KPI.md).

| KPI retenu | Utilité et limite principale |
| --- | --- |
| Note moyenne | Satisfaction déclarée par note, sur le corpus réellement traité. |
| Part d'avis à sentiment négatif | Lecture des verbatims avec les limites du modèle et du mode de collecte. |
| Taux de réponse visible de l'entreprise | Réactivité publique ; non calculable si le statut de réponse est inconnu. |
| Volume d'avis analysés | Couverture du corpus, **pas** mesure directe de satisfaction. |

La distribution complète des sentiments, les irritants et le score santé restent
des analyses complémentaires du produit, pas des KPI Discovery supplémentaires.

## 7. KPIs data et IA

| KPI | Utilite |
| --- | --- |
| Accuracy | Performance globale du modele. |
| Macro F1 | Performance moyenne par classe, utile avec une classe `Neutre` minoritaire. |
| Precision par classe | Fiabilite des labels predits. |
| Recall par classe | Capacite a detecter chaque sentiment. |
| Nombre de corrections humaines | Volume disponible pour l'amelioration continue. |
| Version MLflow de production | Traçabilite du modele utilise. |

## 8. Experience Map — hypothèse de cadrage

Point de vue **supposé** d'une responsable du service client devant suivre les
avis après achat. Les étapes, besoins et irritants sont des hypothèses issues du
cadrage produit : **aucun entretien, questionnaire ou test utilisateur n'a été
réalisé**. Cette carte n'est donc pas une observation du parcours réel.

| Étape du persona | Action et besoin supposés | Irritant possible | Appui proposé et limite |
| --- | --- | --- | --- |
| Réunir les avis | J'essaie d'obtenir un ensemble d'avis et sa provenance. | Sources dispersées, accès parfois refusé. | Import autorisé ou collecte si accessible ; le HTTP 403 Trustpilot empêche la preuve de collecte exhaustive. |
| Contrôler le corpus | Je vérifie dates, notes, doublons et couverture. | Un échantillon peut donner une image trompeuse. | Historique du run et avertissement de représentativité ; la provenance reste à contrôler. |
| Comprendre les signaux | Je compare note et texte, puis lis les avis négatifs. | Une note seule masque le motif ; le modèle peut se tromper. | Sentiment, thèmes lexicaux et verbatims consultables ; relecture humaine nécessaire. |
| Décider d'une priorité | J'isole les problèmes répétitifs et les avis sans réponse connue. | Plusieurs sujets se concurrencent ; certaines données de réponse manquent. | Priorités et KPI contextualisés ; pas d'attribution causale automatique. |
| Partager et suivre | Je présente les constats et vérifie une évolution. | Périodes et sources non comparables. | Tableau de bord et exports, avec source, période et effectif affichés. |

## 9. Perimetre MVP

Le MVP doit demontrer une chaine complete :

1. acquisition d'avis ;
2. stockage et historisation ;
3. prediction de sentiment ;
4. restitution metier ;
5. export ;
6. correction humaine ;
7. reentrainement du modele.

Fonctionnalites incluses :

- analyse Trustpilot ;
- import CSV ;
- API FastAPI ;
- frontend React ;
- execution asynchrone avec Celery ;
- base PostgreSQL ;
- suivi MLflow ;
- benchmark multi-entreprises ;
- boucle de feedback humain ;
- reentrainement depuis l'interface.

Hors MVP :

- deploiement cloud public ;
- gestion multi-utilisateur avancee ;
- durcissement de l'authentification pour la production ;
- monitoring Prometheus/Grafana ;
- integration officielle Google Reviews ;
- modele Transformer fine-tune.

## 10. Cartographie des ressources

| Ressource | Role |
| --- | --- |
| Python | Scraping, ETL, API, ML. |
| Playwright | Collecte des avis Trustpilot. |
| PostgreSQL | Stockage relationnel. |
| scikit-learn | Modele de classification. |
| MLflow | Versioning et registre du modele. |
| FastAPI | API produit. |
| Celery / Redis | Traitements asynchrones. |
| React / TypeScript | Interface utilisateur. |
| Docker Compose | Reproductibilite locale. |
| GitHub Actions | Premiere couche CI/CD. |

## 11. Alignement avec les consignes du projet

| Consigne | Reponse dans le projet |
| --- | --- |
| Cahier des charges | `cahier_des_charges.md` decrit le besoin, le MVP, les KPIs, la veille et la roadmap. |
| Discovery | Personas et Experience Map hypothétique ici ; données, analyses et quatre KPI dans `docs/DISCOVERY_DONNEES_KPI.md`. |
| Veille technologique et réglementaire | Source datée et sourcée dans `docs/VEILLE_TECHNO_REGLEMENTAIRE.md` ; PDF final encore à produire après validation. |
| SWOT | Contenu source dans `docs/SWOT_SOURCE.md` ; slide PowerPoint unique encore à produire après validation. |
| Recolte de donnees | Scraping Trustpilot + import CSV. |
| Organisation de la donnee | Schema PostgreSQL et pipeline d'analyse. |
| Machine Learning | Modele scikit-learn suivi avec MLflow. |
| Dashboard | Interface React avec rapports, benchmark et exports. |
| API | FastAPI avec authentification JWT et roles par organisation. |
| Dockerisation | Tous les services sont definis dans `docker-compose.yml`. |
| DevOps | CI Docker, deploiement automatise sur VM de test existante, rollback manuel, KPI et supervision de test ; voir `docs/DEVOPS_EVIDENCE.md`. |

## 12. Roadmap de soutenance

### Phase 1 - Demonstration produit

- Lancer l'application.
- Montrer l'historique.
- Lancer ou ouvrir une analyse Trustpilot.
- Importer un CSV de test.
- Lire le rapport entreprise.

### Phase 2 - Valeur metier

- Montrer les irritants.
- Montrer les avis critiques.
- Montrer le benchmark multi-entreprises.
- Exporter un rapport PDF ou CSV.

### Phase 3 - Valeur data / IA

- Corriger quelques avis.
- Montrer la qualite IA.
- Montrer le run d'entrainement valide et ses metriques dans MLflow.
- Expliquer la promotion explicite de la version de production.

### Phase 4 - Industrialisation

- Montrer FastAPI `/docs`.
- Expliquer Celery, Redis, PostgreSQL, MLflow.
- Expliquer Docker Compose.
- Presenter les limites et prochaines evolutions.

## 13. Risques principaux

| Risque | Impact | Mitigation |
| --- | --- | --- |
| Changement du HTML Trustpilot | Scraping fragile. | Import CSV comme alternative et tests reguliers. |
| Donnees ambigues | Erreurs de classification. | Correction humaine et reentrainement. |
| Corpus limite | Generalisation imparfaite. | Ajouter plusieurs entreprises et secteurs. |
| Secrets en local | Non adapte production. | Variables d'environnement puis secret manager. |
| Monitoring limite a la VM de test | Aucune garantie de surveillance en production. | Conserver les rapports de sonde et distinguer cette preuve d'un SLA de production. |

## 14. Conclusion du cadrage

Le projet a pivote d'un simple pipeline de scraping vers une solution produit. Il repond aux attentes du sujet en couvrant la collecte, l'organisation, l'analyse IA, la restitution, l'API, la dockerisation et une boucle d'amelioration continue.

La suite doit surtout renforcer la qualite de demonstration : documentation a jour, tests, scenario de soutenance et preuves claires pour chaque consigne.
