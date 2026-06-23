# Rapport technique - Satisfaction Client

## 1. Objectif du projet

Le projet Satisfaction Client transforme des avis clients non structures en indicateurs exploitables pour une entreprise. Il permet de collecter ou importer des avis, de les analyser avec un modele de sentiment proprietaire, de restituer les resultats dans une application web et d'alimenter une boucle d'amelioration continue via des corrections humaines.

La solution repond a une problematique de satisfaction client en aval de la supply chain : comprendre rapidement les irritants lies a la livraison, au service client, au prix, au remboursement, a la qualite produit ou a la conformite des commandes.

## 2. Architecture generale

Le projet est orchestre avec Docker Compose et se compose de plusieurs services complementaires.

| Service | Technologie | Role |
| --- | --- | --- |
| `frontend` | React, Vite, TypeScript | Interface produit pour lancer, comparer et corriger les analyses. |
| `api` | FastAPI | API produit, endpoints securises par cle API. |
| `celery_worker` | Celery | Execution asynchrone des analyses et des reentrainements. |
| `redis` | Redis | Broker et backend de resultats Celery. |
| `postgres_db` | PostgreSQL | Stockage des entreprises, runs, avis, predictions et corrections. |
| `mlflow` | MLflow | Suivi des experimentations et registre de modele. |
| `worker` | Python | Scripts historiques de scraping, ETL et entrainement. |
| `dashboard` | Streamlit | Ancienne interface d'exploration, conservee comme support historique. |

Flux principal :

```text
Utilisateur
  -> React
  -> FastAPI
  -> PostgreSQL
  -> Celery / Redis
  -> Scraping Trustpilot ou import CSV
  -> Prediction sentiment via modele MLflow
  -> PostgreSQL
  -> Rapport React, export CSV/PDF, corrections humaines
```

## 3. Sources de donnees

Deux modes d'acquisition sont disponibles.

### 3.1 Trustpilot

L'utilisateur saisit une entreprise ou une URL Trustpilot. L'API cree un run d'analyse et Celery execute le scraping avec Playwright. Le scraping peut cibler plusieurs pages par note, ce qui permet d'equilibrer les avis entre 1 et 5 etoiles.

Donnees collectees :

- auteur ;
- note ;
- date brute ;
- verbatim ;
- indicateur de reponse entreprise ;
- entreprise associee.

### 3.2 CSV utilisateur

L'utilisateur peut importer un fichier CSV d'avis. Ce mode permet d'analyser des exports clients ou des avis provenant d'autres plateformes sans dependre de Trustpilot.

Le controle avant import verifie :

- le nombre total d'avis ;
- le nombre de lignes exploitables ;
- le nombre de lignes ignorees ;
- les colonnes detectees ;
- un apercu des premiers verbatims.

Les colonnes minimales attendues sont :

- texte de l'avis ;
- note, si disponible.

Les colonnes optionnelles sont :

- auteur ;
- date ;
- reponse entreprise.

## 4. Modele de donnees

L'application produit utilise un schema PostgreSQL dedie.

| Table | Role |
| --- | --- |
| `companies` | Entreprises analysees et source associee. |
| `analysis_runs` | Historique des analyses, statut, duree, source et fichiers produits. |
| `analysis_run_events` | Journal d'execution lisible par l'utilisateur. |
| `reviews` | Avis individuels rattaches a un run. |
| `sentiment_predictions` | Prediction de sentiment et score du modele. |
| `review_topics` | Irritants detectes sur chaque avis. |
| `review_feedback` | Corrections humaines pour ameliorer le modele. |
| `model_training_runs` | Historique des reentrainements lances depuis l'interface. |

Ce modele separe les donnees brutes, les predictions, les corrections et les metadonnees d'execution. Il permet de conserver un historique auditable, de comparer plusieurs entreprises et de reutiliser les corrections pour le reentrainement.

## 5. Pipeline d'analyse

1. L'utilisateur cree une analyse depuis le frontend.
2. FastAPI valide la demande et cree un `analysis_run`.
3. Si une analyse identique est deja active, l'API renvoie un conflit pour eviter les doublons.
4. Le run est envoye dans Celery.
5. Le worker collecte les avis ou relit le CSV importe.
6. Les avis sont nettoyes et normalises.
7. Le modele de sentiment charge depuis MLflow predit un label et un score.
8. Des irritants metier sont detectes par analyse lexicale.
9. Les resultats sont stockes dans PostgreSQL.
10. Le frontend affiche le rapport, les avis, les exports et le journal d'execution.

Les statuts principaux d'un run sont :

- `pending` ;
- `running` ;
- `completed` ;
- `failed` ;
- `empty`.

## 6. Modele de sentiment

Le modele est un classifieur supervise scikit-learn entraine sur des avis annotes.

Caracteristiques :

- vectorisation TF-IDF des verbatims ;
- prise en compte reduite de la note client ;
- classification en trois classes : `Negatif`, `Neutre`, `Positif` ;
- evaluation par accuracy, precision, recall et F1-score ;
- serialisation locale ;
- publication dans MLflow avec alias de production.

La note client est volontairement ponderee afin que le texte garde une influence centrale. Ce choix repond au besoin metier : detecter les cas ou la note et le verbatim racontent des choses differentes.

## 7. Boucle d'amelioration humaine

L'application permet de corriger manuellement le sentiment d'un avis. Les corrections sont stockees dans `review_feedback`, exportables en CSV et integrees au prochain reentrainement.

Le reentrainement :

- combine le corpus historique annote et les corrections humaines ;
- pondere davantage les corrections recentes ;
- cree un snapshot auditable du dataset d'entrainement ;
- evalue le modele sur un split stratifie ;
- publie une nouvelle version dans MLflow ;
- met a jour l'alias de production.

Cette boucle transforme l'application en outil d'amelioration continue plutot qu'en simple dashboard statique.

## 8. API FastAPI

L'API expose les principaux endpoints suivants.

| Endpoint | Role |
| --- | --- |
| `GET /health` | Verification de disponibilite. |
| `POST /analysis-runs` | Creation d'une analyse Trustpilot. |
| `POST /analysis-runs/preview-csv` | Controle avant import CSV. |
| `POST /analysis-runs/import-csv` | Import et analyse d'un CSV. |
| `GET /analysis-runs` | Historique des analyses. |
| `GET /analysis-runs/{run_id}` | Detail d'un run. |
| `POST /analysis-runs/{run_id}/execute` | Relance d'un run. |
| `GET /analysis-runs/{run_id}/events` | Journal d'execution. |
| `GET /analysis-runs/{run_id}/summary` | Rapport synthetique. |
| `GET /analysis-runs/{run_id}/reviews` | Avis pagines et filtrables. |
| `POST /analysis-runs/{run_id}/reviews/{review_id}/feedback` | Correction humaine. |
| `GET /analysis-runs/feedback/quality` | Synthese qualite IA. |
| `GET /analysis-runs/compare` | Benchmark multi-entreprises. |
| `GET /model-training/overview` | Etat du modele de production. |
| `POST /model-training/runs` | Lancement d'un reentrainement. |

Les endpoints metier sont proteges par une cle API transmise dans le header `X-API-Key`. L'endpoint `/health` reste public afin de faciliter les sondes de disponibilite.

## 9. Interface React

Le frontend React/Vite/TypeScript est l'interface principale du produit. Il permet :

- de lancer une analyse Trustpilot ;
- d'importer un CSV avec controle avant import ;
- de suivre l'historique des runs ;
- de consulter le journal d'execution ;
- de visualiser les KPIs d'un rapport entreprise ;
- de comparer plusieurs runs dans un benchmark ;
- de corriger les labels d'avis ;
- de piloter la qualite IA ;
- de declencher un reentrainement ;
- d'exporter les avis, les corrections et les rapports.

L'interface vise un usage par des profils metier : responsable service client, responsable supply chain, analyste data ou direction.

## 10. Restitution metier

Un rapport entreprise contient :

- volume d'avis analyses ;
- note moyenne ;
- confiance IA moyenne ;
- repartition des sentiments ;
- repartition par note ;
- irritants principaux ;
- avis critiques ;
- incoherences note / texte ;
- score sante ;
- priorites recommandees ;
- points de vigilance.

Le benchmark multi-entreprises permet de comparer deux a quatre runs et de detecter :

- l'entreprise la plus a risque ;
- les irritants communs ;
- les irritants propres ;
- les differences de repartition negative ;
- les signaux metier prioritaires.

## 11. Dockerisation et reproductibilite

Le projet se lance avec Docker Compose. Les services applicatifs, la base de donnees, Redis, MLflow et le frontend sont definis dans `docker-compose.yml`.

Commandes principales :

```powershell
docker-compose up -d --build api celery_worker frontend
docker-compose up -d postgres_db mlflow redis
docker-compose logs -f api
docker-compose logs -f celery_worker
```

Cette organisation rend le projet reproductible sur une autre machine equipee de Docker.

## 12. CI/CD et qualite

Une pipeline GitHub Actions existe pour construire l'image Docker et verifier le demarrage minimal. Les tests manuels frequents incluent :

- build du frontend ;
- compilation Python de l'API ;
- verification `git diff --check` ;
- test de l'endpoint `/health` ;
- execution d'analyses Trustpilot ;
- import CSV ;
- correction humaine ;
- reentrainement ;
- export CSV et PDF.

Ameliorations possibles :

- ajouter des tests unitaires FastAPI ;
- tester automatiquement les schemas Pydantic ;
- ajouter un smoke test Docker Compose ;
- publier des artefacts de rapport en CI ;
- mesurer les temps de pipeline.

## 13. Securite et cadre reglementaire

Mesures deja presentes :

- API key sur les endpoints metier ;
- endpoint de sante public limite ;
- variables d'environnement pour la configuration ;
- separation des services Docker ;
- export explicite des donnees.

Points a renforcer pour une production reelle :

- remplacer les secrets de developpement par un gestionnaire de secrets ;
- ajouter une authentification utilisateur ;
- limiter les droits par role ;
- documenter la duree de conservation des avis ;
- anonymiser les auteurs si le contexte d'usage l'exige ;
- formaliser les contraintes RGPD.

## 14. Limites connues

- Le scraping Trustpilot depend de la structure HTML du site.
- Les avis ironiques ou tres courts restent difficiles a classer.
- La classe `Neutre` est plus difficile a apprendre.
- Les corrections humaines doivent rester coherentes pour ne pas degrader le modele.
- Le monitoring technique reste encore limite.
- Le deploiement cloud n'est pas encore automatise.

## 15. Perspectives

Les evolutions les plus pertinentes sont :

1. renforcer les tests automatises ;
2. enrichir le corpus avec plus d'entreprises et de secteurs ;
3. ajouter une classification thematique plus robuste ;
4. brancher d'autres sources d'avis via API ou CSV ;
5. ajouter un monitoring applicatif et metier ;
6. preparer un deploiement cloud de demonstration ;
7. ajouter une authentification utilisateur complete.

## 16. Conclusion technique

Le projet couvre les principales etapes attendues : collecte, organisation, traitement, machine learning, restitution, API, dockerisation et boucle d'amelioration. Il a evolue d'un pipeline de scraping vers une application produit exploitable par une entreprise pour analyser sa satisfaction client et prioriser ses actions.
