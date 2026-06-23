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

| KPI | Utilite |
| --- | --- |
| Nombre d'avis analyses | Mesurer la couverture de l'analyse. |
| Note moyenne | Donner une lecture rapide de la satisfaction declaree. |
| Distribution des sentiments | Comprendre le ressenti texte. |
| Taux d'avis negatifs | Prioriser les actions correctives. |
| Irritants principaux | Identifier les causes d'insatisfaction. |
| Taux de reponse entreprise | Mesurer la reactivite visible. |
| Score sante | Synthese operationnelle pour comparer les entreprises. |

## 7. KPIs data et IA

| KPI | Utilite |
| --- | --- |
| Accuracy | Performance globale du modele. |
| Macro F1 | Performance moyenne par classe, utile avec une classe `Neutre` minoritaire. |
| Precision par classe | Fiabilite des labels predits. |
| Recall par classe | Capacite a detecter chaque sentiment. |
| Nombre de corrections humaines | Volume disponible pour l'amelioration continue. |
| Version MLflow de production | Traçabilite du modele utilise. |

## 8. Experience map

| Etape | Situation actuelle | Reponse de l'application |
| --- | --- | --- |
| Collecte | L'utilisateur lit plusieurs pages d'avis ou exporte manuellement ses donnees. | Scraping Trustpilot ou import CSV. |
| Structuration | Les avis sont disperses. | Stockage PostgreSQL avec historique des runs. |
| Analyse | Lecture manuelle et interpretation subjective. | Modele de sentiment et detection d'irritants. |
| Priorisation | Les sujets critiques sont difficiles a isoler. | Avis critiques, score sante, points de vigilance. |
| Reporting | Synthese manuelle longue a produire. | Dashboard, export CSV et rapport PDF. |
| Amelioration | Les erreurs de modele ne sont pas capitalisees. | Corrections humaines puis reentrainement. |

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
- authentification complete ;
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
| Discovery | Personas, experience map, KPIs et sources de donnees dans ce document. |
| Veille technologique | Comparaison Trustpilot Business, Google Reviews, Avis Verifies, outils BI et services NLP dans le cahier des charges. |
| SWOT | Section dediee dans le cahier des charges. |
| Recolte de donnees | Scraping Trustpilot + import CSV. |
| Organisation de la donnee | Schema PostgreSQL et pipeline d'analyse. |
| Machine Learning | Modele scikit-learn suivi avec MLflow. |
| Dashboard | Interface React avec rapports, benchmark et exports. |
| API | FastAPI securisee par API key. |
| Dockerisation | Tous les services sont definis dans `docker-compose.yml`. |
| DevOps | GitHub, branches, PR, CI Docker, tests manuels documentes. |

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
- Lancer un reentrainement.
- Consulter la nouvelle version MLflow.

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
| Pas de monitoring complet | Visibilite limite en production. | Ajouter logs structures et tableau de bord technique. |

## 14. Conclusion du cadrage

Le projet a pivote d'un simple pipeline de scraping vers une solution produit. Il repond aux attentes du sujet en couvrant la collecte, l'organisation, l'analyse IA, la restitution, l'API, la dockerisation et une boucle d'amelioration continue.

La suite doit surtout renforcer la qualite de demonstration : documentation a jour, tests, scenario de soutenance et preuves claires pour chaque consigne.
